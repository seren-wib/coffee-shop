from datetime import datetime, timezone as dt_timezone

from django.core.cache import cache
from django.db import connection
from rest_framework.test import APITestCase

from common.tests.helpers import auth_client
from orders.models import Order, OrderStatus, Payment, PaymentStatus
from orders.pg import FakePaymentsClient, PgResult
from orders.tests.factories import make_order, make_payment
from products.tests.factories import make_product
from users.tests.factories import make_member

CONFIRM = "/api/payments/confirm/"
FAIL = "/api/payments/fail/"


def done(amount):
    return PgResult(
        ok=True,
        status="DONE",
        total_amount=amount,
        method="카드",
        approved_at=datetime(2026, 11, 20, 5, 4, 2, tzinfo=dt_timezone.utc),
    )


class PaymentApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        FakePaymentsClient.reset()
        self.user = make_member(user_name="홍길동")
        self.client = auth_client(self.user)
        first = make_product(name="브라질 산토스", base_price=15000).options.get()
        second = make_product(name="콜롬비아", base_price=1000).options.get()
        self.order = make_order(self.user, first, quantity=2)  # 30,000
        self.order.items.create(
            option=second,
            product_name="콜롬비아",
            weight_size=second.weight_size,
            grind_type=second.grind_type,
            order_price=0,
            quantity=1,
        )

    def _start(self, client=None):
        return (client or self.client).post(
            f"/api/orders/{self.order.order_id}/payments/"
        )

    def _confirm(self, pg_order_id, amount=30000, client=None):
        return (client or self.client).post(
            CONFIRM,
            {"paymentKey": "tkey_1", "orderId": pg_order_id, "amount": amount},
            format="json",
        )

    def test_fr25_start_payment(self):
        res = self._start()
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(body["amount"], 30000)
        self.assertEqual(body["pg_order_id"], f"{self.order.order_id}-P1")
        self.assertEqual(body["order_name"], "브라질 산토스 외 1건")
        self.assertEqual(body["customer_name"], "홍길동")
        self.assertEqual(
            Payment.objects.filter(
                order=self.order, payment_status=PaymentStatus.READY
            ).count(),
            1,
        )

    def test_fr26_confirm_success(self):
        pg_order_id = self._start().json()["pg_order_id"]
        FakePaymentsClient.script["confirm"] = [done(30000)]
        res = self._confirm(pg_order_id)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.json(),
            {
                "order_id": self.order.order_id,
                "status": "PAID",
                "final_payment_amt": 30000,
            },
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.PAID)

    def test_fr26_confirm_other_members_payment_is_404(self):
        pg_order_id = self._start().json()["pg_order_id"]
        res = self._confirm(pg_order_id, client=auth_client(make_member()))
        self.assertEqual(res.status_code, 404)
        self.assertEqual(FakePaymentsClient.calls, [])

    def test_fr27_amount_mismatch_closes_without_pg(self):
        pg_order_id = self._start().json()["pg_order_id"]
        res = self._confirm(pg_order_id, amount=100)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "PAYMENT_MISMATCH")
        payment = Payment.objects.get(pg_order_id=pg_order_id)
        self.assertEqual(payment.payment_status, PaymentStatus.CANCELLED)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.PENDING)
        self.assertEqual(FakePaymentsClient.calls, [])

    def test_fr27_cancelled_order_cancels_at_pg(self):
        pg_order_id = self._start().json()["pg_order_id"]
        Order.objects.filter(pk=self.order.pk).update(
            order_status=OrderStatus.CANCELLED
        )
        FakePaymentsClient.script["confirm"] = [done(30000)]
        res = self._confirm(pg_order_id)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "ORDER_NOT_PENDING")
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.CANCELLED)

    def test_fr27_payment_cancelled_with_order_skips_pg(self):
        pg_order_id = self._start().json()["pg_order_id"]
        self.client.post(f"/api/orders/{self.order.order_id}/cancel/")
        res = self._confirm(pg_order_id)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "ORDER_NOT_PENDING")
        self.assertEqual(FakePaymentsClient.calls, [])

    def test_fr28_confirm_failure_records_reason(self):
        pg_order_id = self._start().json()["pg_order_id"]
        FakePaymentsClient.script["confirm"] = [
            PgResult(ok=False, code="REJECT_CARD_COMPANY", message="한도 초과")
        ]
        res = self._confirm(pg_order_id)
        self.assertEqual(res.status_code, 402)
        self.assertEqual(res.json()["code"], "PAYMENT_FAILED")
        payment = Payment.objects.get(pg_order_id=pg_order_id)
        self.assertEqual(payment.payment_status, PaymentStatus.FAILED)
        self.assertIn("한도 초과", payment.failure_reason)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.PENDING)

    def test_fr28_payment_window_failure_is_recorded(self):
        pg_order_id = self._start().json()["pg_order_id"]
        res = self.client.post(
            FAIL,
            {"orderId": pg_order_id, "code": "REJECT_CARD_PAYMENT", "message": "거절"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        payment = Payment.objects.get(pg_order_id=pg_order_id)
        self.assertEqual(payment.payment_status, PaymentStatus.FAILED)
        self.assertEqual(payment.failure_reason, "REJECT_CARD_PAYMENT: 거절")
        self.assertEqual(FakePaymentsClient.calls, [])

    def test_fr28_failure_without_order_id_changes_nothing(self):
        self._start()
        res = self.client.post(
            FAIL, {"code": "PAY_PROCESS_CANCELED", "message": "닫음"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            Payment.objects.get(order=self.order).payment_status, PaymentStatus.READY
        )

    def test_fr28_failure_for_other_members_payment_is_404(self):
        pg_order_id = self._start().json()["pg_order_id"]
        res = auth_client(make_member()).post(
            FAIL, {"orderId": pg_order_id, "code": "X", "message": "y"}, format="json"
        )
        self.assertEqual(res.status_code, 404)

    def test_fr29_retry_payment_adds_row(self):
        pg_order_id = self._start().json()["pg_order_id"]
        FakePaymentsClient.script["confirm"] = [
            PgResult(ok=False, code="REJECT_CARD_COMPANY", message="한도 초과")
        ]
        self._confirm(pg_order_id)
        res = self._start()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Payment.objects.filter(order=self.order).count(), 2)

    def test_fr29_paid_order_retry_is_409(self):
        make_payment(self.order, 1, PaymentStatus.SUCCESS, pg_tid="tkey_done")
        Order.objects.filter(pk=self.order.pk).update(order_status=OrderStatus.PAID)
        res = self._start()
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "ALREADY_PAID")

    def test_fr25_cancelled_order_cannot_start_payment(self):
        Order.objects.filter(pk=self.order.pk).update(
            order_status=OrderStatus.CANCELLED
        )
        res = self._start()
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "INVALID_STATE")

    def test_fr25_other_members_order_is_404(self):
        self.assertEqual(
            self._start(client=auth_client(make_member())).status_code, 404
        )

    def test_nfr18_payments_table_has_no_card_columns(self):
        with connection.cursor() as cursor:
            columns = [
                c.name
                for c in connection.introspection.get_table_description(
                    cursor, "payments"
                )
            ]
        for banned in ("card", "number", "cvc", "expiry"):
            self.assertFalse([c for c in columns if banned in c], banned)
