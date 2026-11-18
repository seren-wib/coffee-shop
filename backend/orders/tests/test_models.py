from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from orders.models import CartItem, Courier, OrderStatus, PaymentStatus
from orders.tests.factories import make_order, make_payment
from products.tests.factories import make_product
from users.tests.factories import make_member


class OrderModelTests(TestCase):
    def setUp(self):
        self.user = make_member()
        self.option = make_product().options.get()

    def test_dr15_final_amount_must_be_items_plus_fee(self):
        order = make_order(self.user, self.option)
        order.final_payment_amt = order.total_product_amt
        with self.assertRaises(IntegrityError), transaction.atomic():
            order.save()

    def test_dr14_shipping_fee_is_0_or_3000(self):
        order = make_order(self.user, self.option)
        order.shipping_fee = 2500
        order.final_payment_amt = order.total_product_amt + 2500
        with self.assertRaises(IntegrityError), transaction.atomic():
            order.save()

    def test_dr19_order_status_check(self):
        order = make_order(self.user, self.option)
        order.order_status = "LOST"
        with self.assertRaises(IntegrityError), transaction.atomic():
            order.save()

    def test_fr48_shipped_order_needs_courier_and_tracking(self):
        order = make_order(self.user, self.option)
        order.order_status = OrderStatus.SHIPPED
        with self.assertRaises(IntegrityError), transaction.atomic():
            order.save()
        order.courier_code = Courier.CJ
        order.tracking_number = "123456789012"
        order.shipped_at = timezone.now()
        order.save()

    def test_nfr17_member_with_orders_cannot_be_deleted(self):
        make_order(self.user, self.option)
        with self.assertRaises(ProtectedError):
            self.user.delete()

    def test_dr24_only_one_success_payment_per_order(self):
        order = make_order(self.user, self.option)
        make_payment(order, 1, PaymentStatus.SUCCESS)
        make_payment(order, 2, PaymentStatus.FAILED)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_payment(order, 3, PaymentStatus.SUCCESS)

    def test_dr24_pg_order_id_is_unique(self):
        order = make_order(self.user, self.option)
        make_payment(order, 1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_payment(order, 1)


class CartItemModelTests(TestCase):
    def test_dr9_one_row_per_member_and_option(self):
        user = make_member()
        option = make_product().options.get()
        CartItem.objects.create(user=user, option=option, quantity=2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItem.objects.create(user=user, option=option, quantity=1)

    def test_dr10_quantity_must_be_positive(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItem.objects.create(
                user=make_member(), option=make_product().options.get(), quantity=0
            )
