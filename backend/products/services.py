"""Stock and sales status (SDD 4.7.0, 4.7.6 ~ 4.7.10).

These are the only functions that change product_options.stock_quantity and
products.sales_status (SDD 2.1, 5.9). Every change is a conditional UPDATE, so a
STOPPED product is never overwritten by an automatic switch (DR-7).
"""

from django.db import transaction
from django.db.models import F
from rest_framework import status

from common.exceptions import DomainError
from products.models import Product, ProductOption, SalesStatus


def _not_found():
    return DomainError("NOT_FOUND", "찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)


def _invalid_quantity():
    return DomainError(
        "VALIDATION_ERROR", "수량을 확인해 주세요.", status.HTTP_400_BAD_REQUEST
    )


def _product_id_of(option_id):
    try:
        return ProductOption.objects.values_list("product_id", flat=True).get(
            pk=option_id
        )
    except ProductOption.DoesNotExist:
        raise _not_found() from None


def _mark_sold_out_if_empty(product_id):
    if not ProductOption.objects.filter(
        product_id=product_id, stock_quantity__gt=0
    ).exists():
        Product.objects.filter(pk=product_id, sales_status=SalesStatus.ON_SALE).update(
            sales_status=SalesStatus.SOLD_OUT
        )


def _mark_on_sale_if_sold_out(product_id):
    Product.objects.filter(pk=product_id, sales_status=SalesStatus.SOLD_OUT).update(
        sales_status=SalesStatus.ON_SALE
    )


@transaction.atomic
def decrease_stock(option_id: int, quantity: int) -> None:
    """Order creation (4.5.3). Runs inside the caller's transaction (NFR-14)."""
    if quantity <= 0:
        raise _invalid_quantity()
    updated = ProductOption.objects.filter(
        pk=option_id, stock_quantity__gte=quantity
    ).update(stock_quantity=F("stock_quantity") - quantity)
    if updated == 0:
        raise DomainError("OUT_OF_STOCK", "재고가 부족합니다.")
    _mark_sold_out_if_empty(_product_id_of(option_id))


@transaction.atomic
def increase_stock(option_id: int, quantity: int) -> None:
    """Cancels (4.5.8, 4.8.7). The caller's conditional UPDATE stops a second call (DR-21)."""
    if quantity <= 0:
        raise _invalid_quantity()
    product_id = _product_id_of(option_id)
    ProductOption.objects.filter(pk=option_id).update(
        stock_quantity=F("stock_quantity") + quantity
    )
    _mark_on_sale_if_sold_out(product_id)


@transaction.atomic
def set_stock(option_id: int, quantity: int) -> None:
    """Admin stock adjustment (FR-41) and the stock of a new option (4.7.4)."""
    if quantity < 0:
        raise _invalid_quantity()
    product_id = _product_id_of(option_id)
    ProductOption.objects.filter(pk=option_id).update(stock_quantity=quantity)
    if quantity == 0:
        _mark_sold_out_if_empty(product_id)
    else:
        _mark_on_sale_if_sold_out(product_id)


def _invalid_state_or_not_found(product_id):
    if not Product.objects.filter(pk=product_id).exists():
        return _not_found()
    return DomainError("INVALID_STATE", "지금 상태에서는 할 수 없는 요청입니다.")


@transaction.atomic
def stop_sales(product_id: int) -> None:
    """FR-42: ON_SALE or SOLD_OUT -> STOPPED."""
    updated = Product.objects.filter(
        pk=product_id,
        sales_status__in=[SalesStatus.ON_SALE, SalesStatus.SOLD_OUT],
    ).update(sales_status=SalesStatus.STOPPED)
    if updated == 0:
        raise _invalid_state_or_not_found(product_id)


@transaction.atomic
def resume_sales(product_id: int) -> None:
    """FR-43: STOPPED -> ON_SALE with stock or no options, otherwise SOLD_OUT."""
    options = ProductOption.objects.filter(product_id=product_id)
    if options.filter(stock_quantity__gt=0).exists() or not options.exists():
        new_status = SalesStatus.ON_SALE
    else:
        new_status = SalesStatus.SOLD_OUT
    updated = Product.objects.filter(
        pk=product_id, sales_status=SalesStatus.STOPPED
    ).update(sales_status=new_status)
    if updated == 0:
        raise _invalid_state_or_not_found(product_id)
