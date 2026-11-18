"""create_order as written in SDD 4.5.3.

decrease_stock and _sync_sold_out follow 4.7.6, next_order_id 4.5.2 and
shipping_fee_for 4.4.
"""
from datetime import date

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import CartItem, Order, OrderItem, Product, ProductOption

FREE_SHIPPING_THRESHOLD = 30000
SHIPPING_FEE = 3000


class DomainError(Exception):
    def __init__(self, code, message, status):
        super().__init__(message)
        self.code = code
        self.status = status


def shipping_fee_for(product_amount: int) -> int:
    if product_amount == 0:
        return 0
    return 0 if product_amount >= FREE_SHIPPING_THRESHOLD else SHIPPING_FEE


def next_order_id(today: date) -> str:
    prefix = f"ORD-{today:%Y%m%d}-"
    last = (
        Order.objects.filter(order_id__startswith=prefix)
        .order_by("-order_id")
        .values_list("order_id", flat=True)
        .first()
    )
    seq = int(last[-3:]) + 1 if last else 1
    if seq > 999:
        raise DomainError("ORDER_LIMIT", "order limit reached", 503)
    return f"{prefix}{seq:03d}"


def _sync_sold_out(option_id):
    product_id = ProductOption.objects.values_list("product_id", flat=True).get(pk=option_id)
    if not ProductOption.objects.filter(product_id=product_id, stock_quantity__gt=0).exists():
        Product.objects.filter(pk=product_id, sales_status="ON_SALE").update(
            sales_status="SOLD_OUT"
        )


def decrease_stock(option_id: int, quantity: int) -> None:
    updated = ProductOption.objects.filter(
        pk=option_id, stock_quantity__gte=quantity
    ).update(stock_quantity=F("stock_quantity") - quantity)
    if updated == 0:
        raise DomainError("OUT_OF_STOCK", "out of stock", 409)
    _sync_sold_out(option_id)


def create_order(user_id: int) -> Order:
    try:
        with transaction.atomic():
            items = list(
                CartItem.objects.filter(user_id=user_id).select_related("option__product")
            )
            if not items:
                raise DomainError("EMPTY_CART", "cart is empty", 400)
            if any(i.option.product.sales_status != "ON_SALE" for i in items):
                raise DomainError("NOT_AVAILABLE", "not available", 409)
            for item in items:
                decrease_stock(item.option_id, item.quantity)
            lines = [
                (item, item.option.product.base_price + item.option.extra_price)
                for item in items
            ]
            total = sum(price * item.quantity for item, price in lines)
            fee = shipping_fee_for(total)
            order = Order.objects.create(
                order_id=next_order_id(timezone.localdate()),
                user_id=user_id,
                recipient_name="spike",
                shipping_address="(00000) spike",
                total_product_amt=total,
                shipping_fee=fee,
                final_payment_amt=total + fee,
            )
            OrderItem.objects.bulk_create(
                OrderItem(
                    order=order,
                    option_id=item.option_id,
                    product_name=item.option.product.name,
                    weight_size=item.option.weight_size,
                    grind_type=item.option.grind_type,
                    order_price=price,
                    quantity=item.quantity,
                )
                for item, price in lines
            )
            CartItem.objects.filter(id__in=[i.id for i in items]).delete()
            return order
    except IntegrityError:
        raise DomainError("RETRY", "retry", 409)
