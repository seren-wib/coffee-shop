"""Cart and order rules (SDD 4.4, 4.5). Views and serializers call these; they hold no rules."""

from django.db import transaction
from rest_framework import status

from common.exceptions import DomainError
from orders.models import CartItem
from products.models import ProductOption, SalesStatus

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
