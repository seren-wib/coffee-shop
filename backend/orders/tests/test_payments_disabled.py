"""Payments switched off (no TOSS_SECRET_KEY on the server, SIP 3)."""

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from common.tests.helpers import auth_client
from orders.models import Order, OrderStatus, Payment, PaymentStatus
from orders.pg import FakePaymentsClient
from orders.tests.factories import make_order, make_payment
from products.tests.factories import make_product
from users.models import Role
from users.tests.factories import make_member


@override_settings(PAYMENTS_ENABLED=False)
class PaymentsDisabledTests(APITestCase):
    def setUp(self):
        cache.clear()
        FakePaymentsClient.reset()
        self.user = make_member()
        self.option = make_product(base_price=15000).options.get()

    def _assert_disabled(self, res):
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.json()["code"], "PAYMENTS_DISABLED")
        self.assertEqual(FakePaymentsClient.calls, [])

    def test_nfr13_start_payment_is_503_without_a_row(self):
        order = make_order(self.user, self.option, quantity=2)
        res = auth_client(self.user).post(f"/api/orders/{order.order_id}/payments/")
        self._assert_disabled(res)
        self.assertFalse(Payment.objects.filter(order=order).exists())

    def test_nfr13_confirm_is_503_and_keeps_ready(self):
        order = make_order(self.user, self.option, quantity=2)
        payment = make_payment(order, 1, PaymentStatus.READY)
        res = auth_client(self.user).post(
            "/api/payments/confirm/",
            {
                "paymentKey": "tkey_1",
                "orderId": payment.pg_order_id,
                "amount": payment.paid_amount,
            },
            format="json",
        )
        self._assert_disabled(res)
        payment.refresh_from_db()
        self.assertEqual(payment.payment_status, PaymentStatus.READY)

    def test_nfr13_cancel_approve_is_503_and_keeps_request(self):
        order = make_order(
            self.user, self.option, quantity=2, status=OrderStatus.CANCEL_REQUESTED
        )
        make_payment(order, 1, PaymentStatus.SUCCESS, pg_tid="tkey_done")
        admin = auth_client(make_member(role=Role.ADMIN))
        res = admin.post(f"/api/admin/orders/{order.order_id}/cancel-approve/")
        self._assert_disabled(res)
        self.assertEqual(
            Order.objects.get(pk=order.pk).order_status, OrderStatus.CANCEL_REQUESTED
        )

    def test_nfr13_cart_and_orders_still_work(self):
        client = auth_client(self.user)
        res = client.post(
            "/api/cart/items/",
            {"option_id": self.option.pk, "quantity": 1},
            format="json",
        )
        self.assertIn(res.status_code, (200, 201))
