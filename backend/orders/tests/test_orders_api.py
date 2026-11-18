import re
import threading
from datetime import timedelta

from django.core.cache import cache
from django.db import connection
from django.test import TransactionTestCase, tag
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from common.tests.helpers import auth_client
from orders.models import CartItem, Order, OrderStatus, PaymentStatus
from orders.tests.factories import make_order, make_payment
from products.models import ProductOption, SalesStatus
from products.tests.factories import make_product
from users.models import UserAddress
from users.tests.factories import make_address, make_member

ORDERS = "/api/orders/"


class OrderApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_member()
        self.client = auth_client(self.user)
        self.address = make_address(self.user, is_default=True)
        self.option = make_product(
            base_price=15000, options=[{"stock_quantity": 5}]
        ).options.get()

    def _cart(self, option=None, quantity=1, user=None):
        return CartItem.objects.create(
            user=user or self.user, option=option or self.option, quantity=quantity
        )

    def _order(self, body=None):
        return self.client.post(
            ORDERS, body or {"address_id": self.address.address_id}, format="json"
        )

    def test_fr23_create_order_from_whole_cart(self):
        self._cart(quantity=2)
        res = self._order()
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(body["status"], OrderStatus.PENDING)
        self.assertRegex(body["order_id"], r"^ORD-\d{8}-\d{3}$")
        self.assertEqual(
            body["order_id"][4:12], timezone.localdate().strftime("%Y%m%d")
        )
        self.assertEqual(body["final_payment_amt"], 30000)
        self.assertEqual(ProductOption.objects.get(pk=self.option.pk).stock_quantity, 3)
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())

    def test_fr23_nfr14_one_short_item_rejects_all(self):
        short = make_product(options=[{"stock_quantity": 1}]).options.get()
        self._cart(quantity=2)
        short_item = self._cart(short, 3)
        res = self._order()
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "OUT_OF_STOCK")
        self.assertEqual(
            res.json()["details"], {"cart_item_ids": [short_item.cart_item_id]}
        )
        self.assertEqual(ProductOption.objects.get(pk=self.option.pk).stock_quantity, 5)
        self.assertEqual(ProductOption.objects.get(pk=short.pk).stock_quantity, 1)
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 2)
        self.assertEqual(Order.objects.count(), 0)

    def test_fr23_empty_cart_is_400(self):
        res = self._order()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "EMPTY_CART")

    def test_fr23_new_address_is_copied(self):
        self._cart()
        before = UserAddress.objects.count()
        res = self._order(
            {
                "address": {
                    "recipient_name": "새사람",
                    "recipient_phone": "010-9999-8888",
                    "zipcode": "06236",
                    "base_address": "서울 강남구 테헤란로 1",
                    "detail_address": "",
                }
            }
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["recipient_name"], "새사람")
        self.assertEqual(
            res.json()["shipping_address"], "(06236) 서울 강남구 테헤란로 1"
        )
        self.assertEqual(UserAddress.objects.count(), before)

    def test_fr23_address_is_required_and_must_be_mine(self):
        self._cart()
        self.assertEqual(self.client.post(ORDERS, {}, format="json").status_code, 400)
        theirs = make_address(make_member(), is_default=True)
        res = self._order({"address_id": theirs.address_id})
        self.assertEqual(res.status_code, 404)
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 1)

    def test_nfr16_stopped_product_in_cart_is_409(self):
        item = self._cart()
        self.option.product.sales_status = SalesStatus.STOPPED
        self.option.product.save()
        res = self._order()
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "NOT_AVAILABLE")
        self.assertEqual(res.json()["details"], {"cart_item_ids": [item.cart_item_id]})

    def test_fr30_list_own_orders_newest_first(self):
        old = make_order(self.user, self.option)
        Order.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )
        new = make_order(self.user, self.option)
        make_order(make_member(), self.option)
        res = self.client.get(ORDERS)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["count"], 2)
        self.assertEqual(
            [o["order_id"] for o in body["results"]], [new.order_id, old.order_id]
        )
        self.assertEqual(
            set(body["results"][0]),
            {
                "order_id",
                "created_at",
                "final_payment_amt",
                "status",
                "item_count",
                "first_item_name",
            },
        )

    def test_fr55_filter_own_orders_by_status(self):
        make_order(self.user, self.option)
        paid = make_order(self.user, self.option, status=OrderStatus.PAID)
        res = self.client.get(ORDERS, {"status": "PAID"})
        self.assertEqual(
            [o["order_id"] for o in res.json()["results"]], [paid.order_id]
        )
        self.assertEqual(self.client.get(ORDERS, {"status": "LOST"}).status_code, 400)
        self.assertEqual(self.client.get(ORDERS, {"status": ""}).json()["count"], 2)

    def test_fr31_order_detail(self):
        order = make_order(self.user, self.option, quantity=2)
        make_payment(order, 1, PaymentStatus.FAILED, failure_reason="한도 초과")
        res = self.client.get(f"{ORDERS}{order.order_id}/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["status"], OrderStatus.PENDING)
        self.assertEqual(body["items"][0]["subtotal"], 30000)
        self.assertEqual(body["payments"][0]["status"], PaymentStatus.FAILED)
        self.assertEqual(body["payments"][0]["failure_reason"], "한도 초과")
        self.assertEqual(body["recipient_name"], order.recipient_name)
        self.assertTrue(body["can_pay"])
        self.assertTrue(body["can_cancel"])
        self.assertFalse(body["can_request_cancel"])
        self.assertIsNone(body["tracking_url"])
        self.assertTrue(re.search(r"\+09:00$", body["created_at"]))

    def test_fr31_nfr11_other_members_order_is_404(self):
        theirs = make_order(make_member(), self.option)
        res = self.client.get(f"{ORDERS}{theirs.order_id}/")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(
            self.client.post(f"{ORDERS}{theirs.order_id}/cancel/").status_code, 404
        )

    def test_fr32_cancel_pending_order(self):
        self._cart(quantity=2)
        order_id = self._order().json()["order_id"]
        make_payment(Order.objects.get(pk=order_id), 1)
        res = self.client.post(f"{ORDERS}{order_id}/cancel/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], OrderStatus.CANCELLED)
        self.assertEqual(ProductOption.objects.get(pk=self.option.pk).stock_quantity, 5)
        self.assertEqual(res.json()["payments"][0]["status"], PaymentStatus.CANCELLED)
        self.assertEqual(res.json()["payments"][0]["failure_reason"], "주문 취소")

    def test_fr32_cancel_paid_order_is_409(self):
        order = make_order(self.user, self.option, status=OrderStatus.PAID)
        res = self.client.post(f"{ORDERS}{order.order_id}/cancel/")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "INVALID_STATE")

    def test_fr33_request_cancel(self):
        for status in (OrderStatus.PAID, OrderStatus.PREPARING):
            order = make_order(self.user, self.option, status=status)
            path = f"{ORDERS}{order.order_id}/cancel-request/"
            self.assertEqual(
                self.client.post(path, {"reason": ""}, format="json").status_code, 400
            )
            res = self.client.post(path, {"reason": "단순 변심"}, format="json")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["status"], OrderStatus.CANCEL_REQUESTED)
            order.refresh_from_db()
            self.assertEqual(order.status_before_cancel, status)
            self.assertEqual(order.cancel_reason, "단순 변심")
        shipped = make_order(
            self.user,
            self.option,
            status=OrderStatus.SHIPPED,
            courier_code="CJ",
            tracking_number="1",
            shipped_at=timezone.now(),
        )
        res = self.client.post(
            f"{ORDERS}{shipped.order_id}/cancel-request/",
            {"reason": "단순 변심"},
            format="json",
        )
        self.assertEqual(res.status_code, 409)
        self.assertIn("배송 중", res.json()["message"])

    def test_fr34_shipped_order_shows_tracking(self):
        now = timezone.now()
        order = make_order(
            self.user,
            self.option,
            status=OrderStatus.DELIVERED,
            courier_code="CJ",
            tracking_number="1234-5678",
            shipped_at=now,
            delivered_at=now,
        )
        body = self.client.get(f"{ORDERS}{order.order_id}/").json()
        self.assertEqual(body["courier_name"], "CJ대한통운")
        self.assertEqual(body["tracking_number"], "1234-5678")
        self.assertIn("12345678", body["tracking_url"])
        self.assertIsNotNone(body["delivered_at"])

    def test_fr30_needs_token(self):
        self.assertEqual(APIClient().get(ORDERS).status_code, 401)


@tag("concurrency")
class ConcurrentOrderTests(TransactionTestCase):
    def test_nfr15_last_stock_concurrent_orders(self):
        option = make_product(options=[{"stock_quantity": 1}]).options.get()
        clients = []
        for _ in range(10):
            member = make_member()
            address = make_address(member, is_default=True)
            CartItem.objects.create(user=member, option=option, quantity=1)
            clients.append((auth_client(member), address.address_id))
        barrier = threading.Barrier(len(clients))
        codes = []
        lock = threading.Lock()

        def order(client, address_id):
            try:
                barrier.wait()
                res = client.post(ORDERS, {"address_id": address_id}, format="json")
                with lock:
                    codes.append(res.status_code)
            finally:
                connection.close()

        threads = [threading.Thread(target=order, args=c) for c in clients]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(sorted(codes), [201] + [409] * 9)
        self.assertEqual(ProductOption.objects.get(pk=option.pk).stock_quantity, 0)
        self.assertEqual(Order.objects.count(), 1)
