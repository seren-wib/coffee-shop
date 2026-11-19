"""Cart and order rules (SDD 4.4, 4.5). Views and serializers call these; they hold no rules."""

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError

from common.exceptions import DomainError
from orders.models import (
    CartItem,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentStatus,
)
from orders.order_number import next_order_id
from products.models import ProductOption, SalesStatus
from products.services import decrease_stock, increase_stock
from users.models import UserAddress

SHIPPING_FEE = 3000
FREE_SHIPPING_THRESHOLD = 30000


def shipping_fee_for(product_amount: int) -> int:
    """One rule for cart, order creation and the order screen (DR-14, SDD 4.4.0)."""
    if product_amount == 0:
        return 0
    return 0 if product_amount >= FREE_SHIPPING_THRESHOLD else SHIPPING_FEE


def _not_found():
    return DomainError("NOT_FOUND", "찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)


def _out_of_stock():
    return DomainError("OUT_OF_STOCK", "재고가 부족합니다.")


def _own_cart_item(user, cart_item_id):
    # Owner filter first: another member's item looks like a missing one (NFR-11).
    item = (
        CartItem.objects.select_related("option")
        .filter(user=user, cart_item_id=cart_item_id)
        .first()
    )
    if item is None:
        raise _not_found()
    return item


@transaction.atomic
def add_to_cart(user, option_id: int, quantity: int):
    """Returns (item, created). Stock is not held; orders take it (SRS 2.6)."""
    option = (
        ProductOption.objects.select_related("product").filter(pk=option_id).first()
    )
    if option is None:
        raise _not_found()
    if option.product.sales_status != SalesStatus.ON_SALE:
        raise DomainError("NOT_AVAILABLE", "지금은 담을 수 없는 원두입니다.")
    item = CartItem.objects.filter(user=user, option=option).first()
    new_quantity = (item.quantity if item else 0) + quantity
    if new_quantity > option.stock_quantity:
        raise _out_of_stock()
    if item:
        CartItem.objects.filter(pk=item.pk).update(quantity=new_quantity)
        item.quantity = new_quantity
        return item, False
    return CartItem.objects.create(user=user, option=option, quantity=quantity), True


@transaction.atomic
def change_cart_quantity(user, cart_item_id: int, quantity: int):
    item = _own_cart_item(user, cart_item_id)
    if quantity > item.option.stock_quantity:
        raise _out_of_stock()
    CartItem.objects.filter(pk=item.pk).update(quantity=quantity)
    item.quantity = quantity
    return item


@transaction.atomic
def remove_cart_item(user, cart_item_id: int) -> None:
    _own_cart_item(user, cart_item_id).delete()


def cart_items(user):
    return (
        CartItem.objects.filter(user=user)
        .select_related("option__product")
        .order_by("created_at", "cart_item_id")
    )


def is_available(item) -> bool:
    option = item.option
    return (
        option.product.sales_status == SalesStatus.ON_SALE
        and item.quantity <= option.stock_quantity
    )


def cart_summary(user):
    """Current prices and availability for every item (FR-20)."""
    items = list(cart_items(user))
    product_amount = sum(i.option.price * i.quantity for i in items)
    fee = shipping_fee_for(product_amount)
    return {
        "items": items,
        "product_amount": product_amount,
        "shipping_fee": fee,
        "total_amount": product_amount + fee,
        "can_order": bool(items) and all(is_available(i) for i in items),
    }


# Orders (SDD 4.5). Status changes are conditional UPDATEs on the status read under
# the IMMEDIATE write lock; 0 rows means 409 INVALID_STATE (SDD 4.0, 4.5.1).

# "<modifier> 주문은 ..." so the message names the current status (SDD 4.5.1).
STATUS_MODIFIER = {
    OrderStatus.PENDING: "결제 대기 중인",
    OrderStatus.PAID: "결제 완료된",
    OrderStatus.PREPARING: "배송 준비 중인",
    OrderStatus.SHIPPED: "배송 중인",
    OrderStatus.DELIVERED: "배송 완료된",
    OrderStatus.CANCEL_REQUESTED: "취소 요청된",
    OrderStatus.CANCELLED: "취소된",
}


def invalid_state(current, action):
    return DomainError(
        "INVALID_STATE", f"{STATUS_MODIFIER[current]} 주문은 {action} 수 없습니다."
    )


def filter_by_status(orders, value):
    """?status= for member and admin lists: empty means all, unknown is 400."""
    if not value:
        return orders
    if value not in OrderStatus.values:
        raise ValidationError({"status": ["알 수 없는 주문 상태입니다."]})
    return orders.filter(order_status=value)


def own_order(user, order_id):
    order = Order.objects.filter(user=user, order_id=order_id).first()
    if order is None:
        raise _not_found()
    return order


def _shipping_address(zipcode, base_address, detail_address):
    return f"({zipcode}) {base_address} {detail_address or ''}".strip()


def _address_snapshot(user, address_id, address):
    if address_id is not None:
        saved = UserAddress.objects.filter(user=user, address_id=address_id).first()
        if saved is None:
            raise _not_found()
        address = {
            "recipient_name": saved.recipient_name,
            "recipient_phone": saved.recipient_phone,
            "zipcode": saved.zipcode,
            "base_address": saved.base_address,
            "detail_address": saved.detail_address,
        }
    # A new address is copied into the order only, not saved to the list (FR-23).
    return {
        "recipient_name": address["recipient_name"],
        "recipient_phone": address["recipient_phone"],
        "shipping_address": _shipping_address(
            address["zipcode"], address["base_address"], address.get("detail_address")
        ),
    }


@transaction.atomic
def create_order(user, *, address_id=None, address=None):
    """The whole cart becomes one PENDING order, or nothing changes (FR-23, NFR-14)."""
    items = list(cart_items(user))
    if not items:
        raise DomainError(
            "EMPTY_CART", "주문할 항목이 없습니다.", status.HTTP_400_BAD_REQUEST
        )
    snapshot = _address_snapshot(user, address_id, address)

    # Read under the write lock: the server checks again whatever the screen showed.
    not_available = [
        i.cart_item_id
        for i in items
        if i.option.product.sales_status != SalesStatus.ON_SALE
    ]
    if not_available:
        raise DomainError(
            "NOT_AVAILABLE",
            "주문할 수 없는 원두가 있습니다.",
            details={"cart_item_ids": not_available},
        )
    # List every short item for the screen (UC-5); decrease_stock still guards each one.
    short = [i.cart_item_id for i in items if i.quantity > i.option.stock_quantity]
    if short:
        raise _short_items(short)
    for item in items:
        decrease_stock(item.option.option_id, item.quantity)

    total = sum(i.option.price * i.quantity for i in items)
    fee = shipping_fee_for(total)
    order_id = next_order_id(timezone.localdate())
    try:
        with transaction.atomic():
            order = Order.objects.create(
                order_id=order_id,
                user=user,
                order_status=OrderStatus.PENDING,
                total_product_amt=total,
                shipping_fee=fee,
                final_payment_amt=total + fee,
                **snapshot,
            )
    except IntegrityError:
        # Only a taken order number is a race worth retrying (SDD 4.5.2); any other
        # constraint failure is a bug and must surface as a 500 with a logged trace.
        if not Order.objects.filter(pk=order_id).exists():
            raise
        raise DomainError("RETRY", "잠시 후 다시 시도해 주세요.") from None
    OrderItem.objects.bulk_create(
        OrderItem(
            order=order,
            option=i.option,
            product_name=i.option.product.name,
            weight_size=i.option.weight_size,
            grind_type=i.option.grind_type,
            order_price=i.option.price,
            quantity=i.quantity,
        )
        for i in items
    )
    CartItem.objects.filter(pk__in=[i.pk for i in items]).delete()
    return order


def _short_items(cart_item_ids):
    return DomainError(
        "OUT_OF_STOCK", "재고가 부족합니다.", details={"cart_item_ids": cart_item_ids}
    )


@transaction.atomic
def cancel_pending_order(user, order_id):
    """FR-32. A second call updates 0 rows, so stock comes back once (DR-21)."""
    order = own_order(user, order_id)
    updated = Order.objects.filter(
        pk=order.pk, order_status=OrderStatus.PENDING
    ).update(order_status=OrderStatus.CANCELLED)
    if updated == 0:
        order.refresh_from_db()
        raise invalid_state(order.order_status, "취소할")
    for item in order.items.all():
        increase_stock(item.option_id, item.quantity)
    Payment.objects.filter(order=order, payment_status=PaymentStatus.READY).update(
        payment_status=PaymentStatus.CANCELLED, failure_reason="주문 취소"
    )
    order.refresh_from_db()
    return order


@transaction.atomic
def request_cancel(user, order_id, reason):
    """FR-33. Only from PAID or PREPARING; the status read is the WHERE (DR-20)."""
    order = own_order(user, order_id)
    current = order.order_status
    if current not in (OrderStatus.PAID, OrderStatus.PREPARING):
        raise invalid_state(current, "취소를 요청할")
    updated = Order.objects.filter(pk=order.pk, order_status=current).update(
        order_status=OrderStatus.CANCEL_REQUESTED,
        status_before_cancel=current,
        cancel_reason=reason,
    )
    if updated == 0:
        order.refresh_from_db()
        raise invalid_state(order.order_status, "취소를 요청할")
    order.refresh_from_db()
    return order


# Admin transitions (SDD 4.8). Every one is a conditional UPDATE on the current status.


def admin_order(order_id):
    order = Order.objects.select_related("user").filter(order_id=order_id).first()
    if order is None:
        raise _not_found()
    return order


def _transition(order_id, expected, action, **changes):
    """UPDATE ... WHERE order_status = expected; 0 rows is 409 with the current status."""
    order = admin_order(order_id)
    updated = Order.objects.filter(pk=order.pk, order_status=expected).update(**changes)
    order.refresh_from_db()
    if updated == 0:
        raise invalid_state(order.order_status, action)
    return order


@transaction.atomic
def prepare(order_id):
    """FR-47. A cancel request that got the lock first is not overwritten."""
    return _transition(
        order_id,
        OrderStatus.PAID,
        "배송 준비로 바꿀",
        order_status=OrderStatus.PREPARING,
    )


@transaction.atomic
def ship(order_id, courier_code, tracking_number):
    """FR-48. Courier, tracking number and shipped time in the same UPDATE."""
    return _transition(
        order_id,
        OrderStatus.PREPARING,
        "배송 시작할",
        order_status=OrderStatus.SHIPPED,
        courier_code=courier_code,
        tracking_number=tracking_number,
        shipped_at=timezone.now(),
    )


@transaction.atomic
def deliver(order_id):
    """FR-49."""
    return _transition(
        order_id,
        OrderStatus.SHIPPED,
        "배송 완료로 바꿀",
        order_status=OrderStatus.DELIVERED,
        delivered_at=timezone.now(),
    )


def approve_cancel(order_id):
    """FR-50, DR-21. PG cancel first, outside the transaction (SDD 4.8.7): if the PG
    fails the order stays CANCEL_REQUESTED and the admin can press again."""
    from orders.payments import cancel_success_payment

    order = admin_order(order_id)
    if order.order_status != OrderStatus.CANCEL_REQUESTED:
        raise invalid_state(order.order_status, "취소 승인할")
    success = Payment.objects.filter(
        order=order, payment_status=PaymentStatus.SUCCESS
    ).first()
    if success is not None:
        cancel_success_payment(success, "관리자 취소 승인")
    return _close_cancelled(order_id)


@transaction.atomic
def _close_cancelled(order_id):
    order = _transition(
        order_id,
        OrderStatus.CANCEL_REQUESTED,
        "취소 승인할",
        order_status=OrderStatus.CANCELLED,
    )
    # Only the call that moved the order restores stock, so it happens once (DR-21).
    for item in order.items.all():
        increase_stock(item.option_id, item.quantity)
    return order


@transaction.atomic
def reject_cancel(order_id):
    """FR-51. Back to the status before the request; the reason stays on record."""
    return _transition(
        order_id,
        OrderStatus.CANCEL_REQUESTED,
        "취소 반려할",
        order_status=F("status_before_cancel"),
        status_before_cancel=None,
    )
