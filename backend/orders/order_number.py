"""Order numbers ORD-YYYYMMDD-NNN (SDD 4.5.2, DR-11)."""

from datetime import date

from rest_framework import status

from common.exceptions import DomainError
from orders.models import Order

DAILY_LIMIT = 999


def next_order_id(today: date) -> str:
    """Called inside create_order's IMMEDIATE transaction, so two orders never read
    the same last number. `today` is timezone.localdate(): it resets at Seoul midnight.
    """
    prefix = f"ORD-{today:%Y%m%d}-"
    last = (
        Order.objects.filter(order_id__startswith=prefix)
        .order_by("-order_id")
        .values_list("order_id", flat=True)
        .first()
    )
    seq = int(last[-3:]) + 1 if last else 1
    if seq > DAILY_LIMIT:
        raise DomainError(
            "ORDER_LIMIT",
            "오늘 받을 수 있는 주문 수를 넘었습니다.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return f"{prefix}{seq:03d}"
