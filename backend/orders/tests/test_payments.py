from datetime import datetime, timezone as dt_timezone
from unittest import mock

from django.test import TestCase

from common.exceptions import DomainError
from orders import payments
from orders.models import OrderStatus, Payment, PaymentStatus
from orders.pg import FakePaymentsClient, PgError, PgResult
from orders.tests.factories import make_order, make_payment
from products.tests.factories import make_product
from users.tests.factories import make_member

APPROVED = datetime(2026, 11, 20, 5, 4, 2, tzinfo=dt_timezone.utc)


def done(amount, method="카드"):
    return PgResult(
        ok=True,
        status="DONE",
        total_amount=amount,
        method=method,
        approved_at=APPROVED,
    )


class PaymentServiceTests(TestCase):
    def setUp(self):
        FakePaymentsClient.reset()
        self.user = make_member()
        self.option = make_product(base_price=15000).options.get()
        self.order = make_order(self.user, self.option, quantity=2)  # 30,000

    def _start(self):
        return payments.start_payment(self.user, self.order.order_id)

    def _confirm(self, payment, amount=None):
        return payments.confirm_payment(
            self.user,
            payment_key="tkey_1234567890",
            pg_order_id=payment.pg_order_id,
            amount=amount if amount is not None else payment.paid_amount,
        )

    def test_dr24_each_attempt_gets_new_pg_order_id(self):
        first = self._start()
        second = self._start()
        self.assertEqual(first.pg_order_id, f"{self.order.order_id}-P1")
        self.assertEqual(second.pg_order_id, f"{self.order.order_id}-P2")
        first.refresh_from_db()
        self.assertEqual(first.payment_status, PaymentStatus.CANCELLED)
        self.assertEqual(first.failure_reason, "새 결제 시도로 대체")
        self.assertEqual(Payment.objects.filter(order=self.order).count(), 2)

    def test_dr22_confirm_success_marks_order_paid(self):
        payment = self._start()
        FakePaymentsClient.script["confirm"] = [done(30000)]
        order = self._confirm(payment)
        payment.refresh_from_db()
        self.assertEqual(order.order_status, OrderStatus.PAID)
        self.assertEqual(payment.payment_status, PaymentStatus.SUCCESS)
        self.assertEqual(payment.pg_tid, "tkey_1234567890")
        self.assertEqual(payment.payment_method, "CARD")
        self.assertEqual(payment.approved_at, APPROVED)

    def test_dr22_confirm_twice_does_not_call_pg_again(self):
        payment = self._start()
        FakePaymentsClient.script["confirm"] = [done(30000)]
        self._confirm(payment)
        order = self._confirm(payment)
        self.assertEqual(order.order_status, OrderStatus.PAID)
        self.assertEqual(len(FakePaymentsClient.calls_to("confirm")), 1)

    def test_dr23_amount_mismatch_closes_without_pg(self):
        # Toss refuses a confirm whose amount differs (403 FORBIDDEN_REQUEST, SDD 3.2).
        payment = self._start()
        with self.assertRaises(DomainError) as ctx:
            self._confirm(payment, amount=100)
        self.assertEqual(ctx.exception.code, "PAYMENT_MISMATCH")
        self.assertEqual(ctx.exception.status, 409)
        self.assertEqual(FakePaymentsClient.calls, [])
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.payment_status, PaymentStatus.CANCELLED)
        self.assertEqual(payment.failure_reason, "결제 금액 불일치")
        self.assertEqual(payment.paid_amount, 30000)
        self.assertEqual(self.order.order_status, OrderStatus.PENDING)

    def test_dr23_pg_approves_other_amount_cancels_payment(self):
        payment = self._start()
        FakePaymentsClient.script["confirm"] = [done(100)]
        with self.assertRaises(DomainError) as ctx:
            self._confirm(payment)
        self.assertEqual(ctx.exception.code, "PAYMENT_MISMATCH")
        cancels = FakePaymentsClient.calls_to("cancel")
        self.assertEqual(len(cancels), 1)
        self.assertEqual(cancels[0]["payment_key"], "tkey_1234567890")
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.payment_status, PaymentStatus.CANCELLED)
        self.assertEqual(payment.failure_reason, "결제 금액 불일치")
        self.assertEqual(payment.paid_amount, 100)
        self.assertEqual(self.order.order_status, OrderStatus.PENDING)

    def test_dr23_success_on_cancelled_order_is_cancelled(self):
        payment = self._start()
        # The member cancels while the approval is in flight: the order is
        # CANCELLED but this payment row is still READY.
        type(self.order).objects.filter(pk=self.order.pk).update(
            order_status=OrderStatus.CANCELLED
        )
        FakePaymentsClient.script["confirm"] = [done(30000)]
        with self.assertRaises(DomainError) as ctx:
            self._confirm(payment)
        self.assertEqual(ctx.exception.code, "ORDER_NOT_PENDING")
        self.assertEqual(len(FakePaymentsClient.calls_to("cancel")), 1)
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.payment_status, PaymentStatus.CANCELLED)
        self.assertEqual(payment.failure_reason, "이미 취소된 주문")
        self.assertEqual(self.order.order_status, OrderStatus.CANCELLED)

    def test_dr24_failure_keeps_order_pending(self):
        payment = self._start()
        FakePaymentsClient.script["confirm"] = [
            PgResult(ok=False, code="REJECT_CARD_COMPANY", message="한도 초과")
        ]
        with self.assertRaises(DomainError) as ctx:
            self._confirm(payment)
        self.assertEqual(ctx.exception.code, "PAYMENT_FAILED")
        self.assertEqual(ctx.exception.status, 402)
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.payment_status, PaymentStatus.FAILED)
        self.assertEqual(payment.failure_reason, "REJECT_CARD_COMPANY: 한도 초과")
        self.assertEqual(self.order.order_status, OrderStatus.PENDING)

    def test_fr26_timeout_keeps_payment_ready(self):
        payment = self._start()
        FakePaymentsClient.script["confirm"] = [PgError("TIMEOUT", "시간 초과")]
        with self.assertRaises(DomainError) as ctx:
            self._confirm(payment)
        self.assertEqual(ctx.exception.code, "PG_ERROR")
        self.assertEqual(ctx.exception.status, 502)
        payment.refresh_from_db()
        self.assertEqual(payment.payment_status, PaymentStatus.READY)

    def test_fr26_already_processed_reads_payment_from_pg(self):
        payment = self._start()
        FakePaymentsClient.script["confirm"] = [
            PgResult(ok=False, code="ALREADY_PROCESSED_PAYMENT", message="이미 처리")
        ]
        FakePaymentsClient.script["get"] = [done(30000)]
        order = self._confirm(payment)
        self.assertEqual(order.order_status, OrderStatus.PAID)
        self.assertEqual(len(FakePaymentsClient.calls_to("get")), 1)

    def test_dr21_cancel_treats_already_cancelled_as_success(self):
        payment = make_payment(self.order, 1, PaymentStatus.SUCCESS, pg_tid="tkey_done")
        FakePaymentsClient.script["cancel"] = [
            PgResult(ok=False, code="ALREADY_CANCELED_PAYMENT", message="이미 취소")
        ]
        payments.cancel_success_payment(payment, "관리자 취소 승인")
        payment.refresh_from_db()
        self.assertEqual(payment.payment_status, PaymentStatus.CANCELLED)
        self.assertEqual(payment.failure_reason, "관리자 취소 승인")

    def test_fr50_cancel_sends_idempotency_key(self):
        payment = make_payment(self.order, 1, PaymentStatus.SUCCESS, pg_tid="tkey_done")
        payments.cancel_success_payment(payment, "관리자 취소 승인")
        call = FakePaymentsClient.calls_to("cancel")[0]
        self.assertEqual(call["idempotency_key"], f"cancel-{payment.payment_id}")
        self.assertEqual(call["payment_key"], "tkey_done")

    def test_fr50_other_pg_cancel_error_raises_pg_error(self):
        payment = make_payment(self.order, 1, PaymentStatus.SUCCESS, pg_tid="tkey_done")
        FakePaymentsClient.script["cancel"] = [
            PgResult(ok=False, code="PROVIDER_ERROR", message="잠시 후")
        ]
        with self.assertRaises(DomainError) as ctx:
            payments.cancel_success_payment(payment, "관리자 취소 승인")
        self.assertEqual(ctx.exception.code, "PG_ERROR")
        payment.refresh_from_db()
        self.assertEqual(payment.payment_status, PaymentStatus.SUCCESS)


class PaymentRaceTests(TestCase):
    """Review findings on PR for SDD 4.6: approvals that cannot stand are refunded."""

    def setUp(self):
        FakePaymentsClient.reset()
        self.user = make_member()
        option = make_product(base_price=15000).options.get()
        self.order = make_order(self.user, option, quantity=2)  # 30,000
        self.payment = payments.start_payment(self.user, self.order.order_id)

    def _confirm(self):
        return payments.confirm_payment(
            self.user,
            payment_key="tkey_race",
            pg_order_id=self.payment.pg_order_id,
            amount=30000,
        )

    def test_dr24_attempt_replaced_during_approval_is_refunded(self):
        real_confirm = FakePaymentsClient.confirm

        def confirm_while_new_attempt_starts(client, *args):
            payments.start_payment(self.user, self.order.order_id)
            return real_confirm(client, *args)

        with mock.patch.object(
            FakePaymentsClient, "confirm", confirm_while_new_attempt_starts
        ):
            with self.assertRaises(DomainError) as ctx:
                self._confirm()
        self.assertEqual(ctx.exception.code, "INVALID_STATE")
        self.order.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.PENDING)
        self.assertEqual(self.payment.payment_status, PaymentStatus.CANCELLED)
        self.assertEqual(self.payment.pg_tid, "tkey_race")
        self.assertEqual(len(FakePaymentsClient.calls_to("cancel")), 1)
        self.assertFalse(
            Payment.objects.filter(payment_status=PaymentStatus.SUCCESS).exists()
        )

    def test_dr24_second_success_on_same_order_is_refunded_as_already_paid(self):
        make_payment(self.order, 9, PaymentStatus.SUCCESS, pg_tid="tkey_other")
        with self.assertRaises(DomainError) as ctx:
            self._confirm()
        self.assertEqual(ctx.exception.code, "ALREADY_PAID")
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.payment_status, PaymentStatus.CANCELLED)
        self.assertEqual(self.payment.failure_reason, "이미 결제된 주문")
        self.assertEqual(len(FakePaymentsClient.calls_to("cancel")), 1)

    def test_fr26_status_other_than_done_is_not_paid(self):
        FakePaymentsClient.script["confirm"] = [
            PgResult(ok=True, status="WAITING_FOR_DEPOSIT", total_amount=30000)
        ]
        with self.assertRaises(DomainError) as ctx:
            self._confirm()
        self.assertEqual(ctx.exception.code, "PAYMENT_FAILED")
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.PENDING)

    def test_fr26_already_processed_but_cancelled_at_pg_is_not_paid(self):
        FakePaymentsClient.script["confirm"] = [
            PgResult(ok=False, code="ALREADY_PROCESSED_PAYMENT", message="이미 처리")
        ]
        FakePaymentsClient.script["get"] = [
            PgResult(ok=True, status="CANCELED", total_amount=30000)
        ]
        with self.assertRaises(DomainError):
            self._confirm()
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.PENDING)

    def test_fr26_already_processed_for_another_order_is_not_paid(self):
        FakePaymentsClient.script["confirm"] = [
            PgResult(ok=False, code="ALREADY_PROCESSED_PAYMENT", message="이미 처리")
        ]
        FakePaymentsClient.script["get"] = [
            PgResult(
                ok=True,
                status="DONE",
                total_amount=30000,
                order_id="ORD-20261120-999-P1",
            )
        ]
        with self.assertRaises(DomainError):
            self._confirm()
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.PENDING)
