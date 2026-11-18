"""Payment rules (SDD 4.6): start, confirm, payment window failure, cancel a success.

PG calls happen outside DB transactions: no write lock is held while waiting for
Toss (SDD 4.0). Payment status changes are conditional UPDATEs on READY or SUCCESS.
"""

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status

from common.exceptions import DomainError
from orders.models import Order, OrderStatus, Payment, PaymentMethod, PaymentStatus
from orders.pg import PgError, PgResult, get_client, masked
from orders.services import own_order

logger = logging.getLogger(__name__)

TOSS_METHODS = {
    "카드": PaymentMethod.CARD,
    "간편결제": PaymentMethod.EASY_PAY,
    "계좌이체": PaymentMethod.TRANSFER,
}
REPLACED = "새 결제 시도로 대체"
MISMATCH = "결제 금액 불일치"
ORDER_GONE = "이미 취소된 주문"


def _pg_error():
    return DomainError(
        "PG_ERROR",
        "결제 확인이 늦어지고 있습니다. 잠시 후 다시 확인해 주세요.",
        status.HTTP_502_BAD_GATEWAY,
    )


def _not_found():
    return DomainError("NOT_FOUND", "찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)


def order_name(order):
    items = list(order.items.order_by("order_item_id"))
    first = items[0].product_name
    return first if len(items) == 1 else f"{first} 외 {len(items) - 1}건"


@transaction.atomic
def start_payment(user, order_id):
    """FR-25, FR-29. One open attempt per order: an older READY row is replaced."""
    order = own_order(user, order_id)
    if Payment.objects.filter(
        order=order, payment_status=PaymentStatus.SUCCESS
    ).exists():
        raise DomainError("ALREADY_PAID", "이미 결제된 주문입니다.")
    if order.order_status != OrderStatus.PENDING:
        raise DomainError("INVALID_STATE", "결제할 수 없는 주문입니다.")
    Payment.objects.filter(order=order, payment_status=PaymentStatus.READY).update(
        payment_status=PaymentStatus.CANCELLED, failure_reason=REPLACED
    )
    attempt = Payment.objects.filter(order=order).count() + 1
    return Payment.objects.create(
        order=order,
        pg_provider="TOSS",
        pg_order_id=f"{order.order_id}-P{attempt}",
        payment_status=PaymentStatus.READY,
        paid_amount=order.final_payment_amt,
    )


def _own_payment(user, pg_order_id):
    payment = (
        Payment.objects.select_related("order")
        .filter(pg_order_id=pg_order_id, order__user=user)
        .first()
    )
    if payment is None:
        raise _not_found()
    return payment


def confirm_payment(user, *, payment_key, pg_order_id, amount):
    """FR-26 ~ FR-28, DR-22 ~ DR-24. Returns the PAID order or raises DomainError."""
    payment = _own_payment(user, pg_order_id)
    order = payment.order
    if payment.payment_status == PaymentStatus.SUCCESS:
        return order  # refreshed result page: same answer, no second PG call
    if payment.payment_status != PaymentStatus.READY:
        if order.order_status == OrderStatus.CANCELLED:
            # Cancelled with the order before approval; Toss takes no money
            # until confirm is called, so there is nothing to cancel at the PG.
            raise _closed(ORDER_GONE)
        raise DomainError("INVALID_STATE", "이미 끝난 결제입니다.")

    client = get_client()
    try:
        result = client.confirm(payment_key, pg_order_id, amount)
        if not result.ok and result.code == "ALREADY_PROCESSED_PAYMENT":
            # Approved earlier but our write was lost: read the PG state (SDD 4.6.3).
            result = client.get(payment_key)
            if result.ok and result.order_id not in (None, pg_order_id):
                result = PgResult(ok=False, code="ORDER_MISMATCH", message=None)
    except PgError as e:
        logger.warning("confirm %s payment_id=%s", e.code, payment.payment_id)
        raise _pg_error() from None  # status unknown: keep READY

    if not result.approved:
        reason = f"{result.code or result.status}: {result.message or ''}"
        Payment.objects.filter(
            pk=payment.pk, payment_status=PaymentStatus.READY
        ).update(payment_status=PaymentStatus.FAILED, failure_reason=reason[:500])
        raise DomainError(
            "PAYMENT_FAILED",
            result.message or "결제에 실패했습니다.",
            status.HTTP_402_PAYMENT_REQUIRED,
        )

    method = TOSS_METHODS.get(result.method, PaymentMethod.OTHER)
    outcome = _mark_paid(payment, order, payment_key, method, result)
    if outcome == PAID:
        order.refresh_from_db()
        return order

    # Approved but it cannot stand: refund at the PG, close the payment with the
    # reason, and tell the member why (DR-23, FR-27).
    try:
        cancel = client.cancel(
            payment_key, outcome, idempotency_key=f"cancel-{payment.payment_id}"
        )
    except PgError:
        raise _pg_error() from None
    if not cancel.ok and cancel.code != "ALREADY_CANCELED_PAYMENT":
        logger.error(
            "pg cancel failed payment_id=%s key=%s code=%s",
            payment.payment_id,
            masked(payment_key),
            cancel.code,
        )
        raise _pg_error()
    # READY, or CANCELLED by a newer attempt meanwhile: either way record the refund.
    Payment.objects.filter(
        pk=payment.pk,
        payment_status__in=[PaymentStatus.READY, PaymentStatus.CANCELLED],
    ).update(
        payment_status=PaymentStatus.CANCELLED,
        pg_tid=payment_key,
        failure_reason=outcome,
    )
    raise _closed(outcome)


PAID = "PAID"
ALREADY_PAID = "이미 결제된 주문"
CLOSED_ERRORS = {
    MISMATCH: ("PAYMENT_MISMATCH", "결제 금액이 주문 금액과 달라 취소했습니다."),
    ORDER_GONE: ("ORDER_NOT_PENDING", "이미 취소된 주문이라 결제를 취소했습니다."),
    ALREADY_PAID: ("ALREADY_PAID", "이미 결제된 주문이라 이 결제를 취소했습니다."),
    REPLACED: ("INVALID_STATE", "새 결제가 시작돼 이 결제를 취소했습니다."),
}


def _closed(reason):
    code, message = CLOSED_ERRORS[reason]
    return DomainError(code, message)


def _mark_paid(payment, order, payment_key, method, result):
    """mark_paid in SDD 4.5.1: the payment becomes SUCCESS first, and the order PAID
    only in the same savepoint. Returns PAID or the reason the approval cannot stand."""
    with transaction.atomic():
        recorded = Payment.objects.filter(
            pk=payment.pk, payment_status=PaymentStatus.READY
        ).update(
            pg_tid=payment_key,
            payment_method=method,
            paid_amount=result.total_amount,
        )
    if recorded == 0:
        return REPLACED  # a newer attempt closed this one while the PG approved it
    if result.total_amount != order.final_payment_amt:
        return MISMATCH
    try:
        with transaction.atomic():
            success = Payment.objects.filter(
                pk=payment.pk, payment_status=PaymentStatus.READY
            ).update(
                payment_status=PaymentStatus.SUCCESS,
                approved_at=result.approved_at or timezone.now(),
            )
            if success == 0:
                return REPLACED
            paid = Order.objects.filter(
                pk=order.pk, order_status=OrderStatus.PENDING
            ).update(order_status=OrderStatus.PAID)
            if paid == 0:
                # Undo the SUCCESS above; read why only after the savepoint ends.
                transaction.set_rollback(True)
    except IntegrityError:
        # Another approval already made this order's one SUCCESS (uq_payments_order_success).
        return ALREADY_PAID
    if paid == 0:
        return _not_pending_reason(order)
    return PAID


def _not_pending_reason(order):
    current = Order.objects.values_list("order_status", flat=True).get(pk=order.pk)
    return ORDER_GONE if current == OrderStatus.CANCELLED else ALREADY_PAID


@transaction.atomic
def fail_payment(user, *, pg_order_id=None, code="", message=""):
    """FR-28. The payment window failed; closing the window sends no orderId."""
    if not pg_order_id:
        return
    payment = _own_payment(user, pg_order_id)
    Payment.objects.filter(pk=payment.pk, payment_status=PaymentStatus.READY).update(
        payment_status=PaymentStatus.FAILED,
        failure_reason=f"{code}: {message}"[:500],
    )


def cancel_success_payment(payment, reason):
    """FR-50 (called by admin cancel approval, SDD 4.6.6). Same key, same result."""
    try:
        result = get_client().cancel(
            payment.pg_tid, reason, idempotency_key=f"cancel-{payment.payment_id}"
        )
    except PgError:
        raise _pg_error() from None
    if not result.ok and result.code != "ALREADY_CANCELED_PAYMENT":
        logger.error(
            "pg cancel failed payment_id=%s code=%s", payment.payment_id, result.code
        )
        raise _pg_error()
    Payment.objects.filter(pk=payment.pk, payment_status=PaymentStatus.SUCCESS).update(
        payment_status=PaymentStatus.CANCELLED, failure_reason=reason
    )
