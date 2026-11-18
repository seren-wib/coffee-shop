from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from orders.models import Order, OrderItem, OrderStatus, Payment, PaymentStatus
from products.models import Product, ProductOption, SalesStatus
from products.origins import ORIGINS
from users.models import Role, User, UserAddress

SMALL = ["--products", "5", "--members", "3", "--orders", "14"]


def seed(*args):
    out = StringIO()
    call_command("seed_demo", *args, stdout=out)
    return out.getvalue()


def snapshot():
    """Everything the seed decides, without generated keys, times or passwords."""
    return {
        "products": list(
            Product.objects.order_by("product_id").values_list(
                "name", "origin", "roast_level", "base_price", "sales_status"
            )
        ),
        "options": list(
            ProductOption.objects.order_by("option_id").values_list(
                "product__name",
                "weight_size",
                "grind_type",
                "extra_price",
                "stock_quantity",
            )
        ),
        "members": list(
            User.objects.filter(role=Role.MEMBER)
            .order_by("user_id")
            .values_list("email", "user_name", "phone_number")
        ),
        "addresses": list(
            UserAddress.objects.order_by("address_id").values_list(
                "user__email", "zipcode", "base_address", "is_default"
            )
        ),
        "orders": list(
            Order.objects.order_by("created_at", "order_id").values_list(
                "user__email", "order_status", "total_product_amt", "shipping_fee"
            )
        ),
        "items": list(
            OrderItem.objects.order_by(
                "order__created_at", "order_item_id"
            ).values_list(
                "product_name", "weight_size", "grind_type", "order_price", "quantity"
            )
        ),
    }


def wipe():
    Payment.objects.all().delete()
    Order.objects.all().delete()
    User.objects.all().delete()
    Product.objects.all().delete()


@override_settings(DEBUG=True)
class SeedDemoTests(TestCase):
    def test_nfr3_seed_demo_counts(self):
        output = seed(*SMALL)
        self.assertEqual(Product.objects.count(), 5)
        self.assertEqual(User.objects.filter(role=Role.MEMBER).count(), 3)
        self.assertEqual(Order.objects.count(), 14)
        for product in Product.objects.all():
            self.assertIn(product.origin, ORIGINS)
            self.assertTrue(1 <= product.options.count() <= 9)
        for user in User.objects.all():
            self.assertTrue(1 <= user.addresses.count() <= 3)
            self.assertEqual(user.addresses.filter(is_default=True).count(), 1)
            self.assertIsNotNone(user.privacy_agreed_at)
        self.assertIn("password", output.lower())

    def test_nfr3_same_seed_gives_same_data(self):
        seed(*SMALL)
        first = snapshot()
        wipe()
        seed(*SMALL)
        self.assertEqual(snapshot(), first)

    def test_nfr3_orders_cover_every_status_with_matching_rows(self):
        seed(*SMALL)
        counts = {s: Order.objects.filter(order_status=s).count() for s in OrderStatus}
        self.assertEqual(set(counts.values()), {2})

        for order in Order.objects.prefetch_related("items", "payments"):
            items_total = sum(i.order_price * i.quantity for i in order.items.all())
            self.assertEqual(order.total_product_amt, items_total)
            self.assertEqual(order.shipping_fee, 0 if items_total >= 30000 else 3000)
            self.assertRegex(order.order_id, r"^ORD-\d{8}-\d{3}$")
            statuses = [p.payment_status for p in order.payments.all()]
            if order.order_status == OrderStatus.PENDING:
                self.assertEqual(statuses, [PaymentStatus.READY])
            elif order.order_status == OrderStatus.CANCELLED:
                self.assertEqual(statuses, [PaymentStatus.CANCELLED])
                self.assertIsNotNone(order.cancel_reason)
            else:
                self.assertEqual(statuses, [PaymentStatus.SUCCESS])
            if order.order_status == OrderStatus.CANCEL_REQUESTED:
                self.assertIn(
                    order.status_before_cancel,
                    [OrderStatus.PAID, OrderStatus.PREPARING],
                )

    def test_nfr3_stock_matches_live_orders(self):
        seed(*SMALL)
        for product in Product.objects.all():
            has_stock = product.options.filter(stock_quantity__gt=0).exists()
            if product.sales_status == SalesStatus.SOLD_OUT:
                self.assertFalse(has_stock)
            if product.sales_status == SalesStatus.ON_SALE:
                self.assertTrue(has_stock)

    def test_nfr3_refuses_a_database_with_data(self):
        seed(*SMALL)
        with self.assertRaises(CommandError):
            seed(*SMALL)

    @override_settings(DEBUG=False)
    def test_nfr3_needs_force_when_debug_is_off(self):
        with self.assertRaises(CommandError):
            seed(*SMALL)
        self.assertEqual(Product.objects.count(), 0)
        seed(*SMALL, "--force")
        self.assertEqual(Product.objects.count(), 5)
