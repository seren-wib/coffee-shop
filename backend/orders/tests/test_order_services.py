from django.test import TestCase
from django.utils import timezone

from common.exceptions import DomainError
from orders import couriers, services
from orders.models import CartItem, Order, OrderStatus
from orders.tests.factories import make_order
from products.models import Product, ProductOption
from products.tests.factories import make_product
from users.tests.factories import make_address, make_member


class CreateOrderServiceTests(TestCase):
    def setUp(self):
        self.user = make_member()
        self.address = make_address(self.user, is_default=True, detail_address="101호")

    def _cart(self, option, quantity):
        CartItem.objects.create(user=self.user, option=option, quantity=quantity)

    def test_dr15_final_amount_is_items_plus_fee(self):
        self._cart(make_product(base_price=14500).options.get(), 2)
        order = services.create_order(self.user, address_id=self.address.address_id)
        self.assertEqual(order.total_product_amt, 29000)
        self.assertEqual(order.shipping_fee, 3000)
        self.assertEqual(order.final_payment_amt, 32000)

    def test_dr12_dr18_order_copies_product_and_address(self):
        product = make_product(name="예가체프", base_price=18000)
        self._cart(product.options.get(), 1)
        order = services.create_order(self.user, address_id=self.address.address_id)
        Product.objects.filter(pk=product.pk).update(name="바뀐 이름", base_price=1)
        self.address.base_address = "바뀐 주소"
        self.address.save()
        order.refresh_from_db()
        item = order.items.get()
        self.assertEqual(item.product_name, "예가체프")
        self.assertEqual(item.order_price, 18000)
        self.assertEqual(
            order.shipping_address, "(28644) 충북 청주시 서원구 충대로 1 101호"
        )

    def test_fr23_nfr14_short_item_rolls_back_whole_order(self):
        ok = make_product(options=[{"stock_quantity": 5}]).options.get()
        short = make_product(options=[{"stock_quantity": 1}]).options.get()
        self._cart(ok, 2)
        self._cart(short, 2)
        with self.assertRaises(DomainError) as ctx:
            services.create_order(self.user, address_id=self.address.address_id)
        self.assertEqual(ctx.exception.code, "OUT_OF_STOCK")
        short_item = CartItem.objects.get(option=short)
        self.assertEqual(
            ctx.exception.details, {"cart_item_ids": [short_item.cart_item_id]}
        )
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(ProductOption.objects.get(pk=ok.pk).stock_quantity, 5)
        self.assertEqual(ProductOption.objects.get(pk=short.pk).stock_quantity, 1)
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 2)

    def test_dr21_cancel_pending_twice_restores_stock_once(self):
        option = make_product(options=[{"stock_quantity": 5}]).options.get()
        self._cart(option, 2)
        order = services.create_order(self.user, address_id=self.address.address_id)
        services.cancel_pending_order(self.user, order.order_id)
        with self.assertRaises(DomainError) as ctx:
            services.cancel_pending_order(self.user, order.order_id)
        self.assertEqual(ctx.exception.code, "INVALID_STATE")
        self.assertEqual(ProductOption.objects.get(pk=option.pk).stock_quantity, 5)

    def test_dr20_no_cancel_request_from_shipped(self):
        option = make_product().options.get()
        for status in (
            OrderStatus.PENDING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED,
            OrderStatus.CANCEL_REQUESTED,
        ):
            extra = {}
            if status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
                extra = {
                    "courier_code": "CJ",
                    "tracking_number": "1",
                    "shipped_at": timezone.now(),
                }
            order = make_order(self.user, option, status=status, **extra)
            with self.assertRaises(DomainError) as ctx:
                services.request_cancel(self.user, order.order_id, "단순 변심")
            self.assertEqual(ctx.exception.code, "INVALID_STATE")
            order.refresh_from_db()
            self.assertEqual(order.order_status, status)


class CourierTests(TestCase):
    def test_fr35_tracking_url_strips_dash_and_encodes(self):
        url = couriers.tracking_url("CJ", "1234-5678-9012")
        self.assertIn("123456789012", url)
        self.assertNotIn("-5678", url)
        for code in ("CJ", "HANJIN", "LOTTE", "EPOST", "LOGEN"):
            self.assertTrue(couriers.tracking_url(code, "12345").startswith("https://"))
        self.assertEqual(couriers.courier_name("EPOST"), "우체국택배")
        self.assertIsNone(couriers.tracking_url(None, None))


class AdminTransitionTests(TestCase):
    """SDD 4.5.1: any (current, action) pair not in the table is 409 INVALID_STATE."""

    ALLOWED = {
        "prepare": {OrderStatus.PAID},
        "ship": {OrderStatus.PREPARING},
        "deliver": {OrderStatus.SHIPPED},
        "approve_cancel": {OrderStatus.CANCEL_REQUESTED},
        "reject_cancel": {OrderStatus.CANCEL_REQUESTED},
    }

    def setUp(self):
        self.user = make_member()
        self.option = make_product(options=[{"stock_quantity": 5}]).options.get()

    def _order(self, status):
        extra = {}
        if status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            extra = {
                "courier_code": "CJ",
                "tracking_number": "1",
                "shipped_at": timezone.now(),
            }
        if status == OrderStatus.CANCEL_REQUESTED:
            extra = {"status_before_cancel": OrderStatus.PAID}
        return make_order(self.user, self.option, status=status, **extra)

    def _call(self, action, order):
        if action == "ship":
            return services.ship(order.order_id, "CJ", "123")
        return getattr(services, action)(order.order_id)

    def test_dr19_disallowed_transitions_raise_invalid_state(self):
        for action, allowed in self.ALLOWED.items():
            for status in OrderStatus.values:
                if status in allowed:
                    continue
                order = self._order(status)
                with self.assertRaises(
                    DomainError, msg=f"{action} from {status}"
                ) as ctx:
                    self._call(action, order)
                self.assertEqual(ctx.exception.code, "INVALID_STATE")
                order.refresh_from_db()
                self.assertEqual(order.order_status, status)

    def test_dr21_cancel_restores_stock_once(self):
        order = self._order(OrderStatus.CANCEL_REQUESTED)  # quantity 1
        services.approve_cancel(order.order_id)
        with self.assertRaises(DomainError) as ctx:
            services.approve_cancel(order.order_id)
        self.assertEqual(ctx.exception.code, "INVALID_STATE")
        self.assertEqual(ProductOption.objects.get(pk=self.option.pk).stock_quantity, 6)
