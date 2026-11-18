"""Read-side querysets for products (SDD 4.3.0 ~ 4.3.5). No django-filter."""

from django.db.models import Case, F, IntegerField, Min, Prefetch, Value, When
from django.db.models.functions import Coalesce
from rest_framework.exceptions import ValidationError

from products.models import (
    GrindType,
    Product,
    ProductOption,
    RoastLevel,
    SalesStatus,
    WeightSize,
)

_WEIGHT_ORDER = [WeightSize.G200, WeightSize.G500, WeightSize.KG1]
_GRIND_ORDER = [GrindType.WHOLE_BEAN, GrindType.HAND_DRIP, GrindType.ESPRESSO]


def _rank(field, values):
    return Case(
        *[When(**{field: v}, then=Value(i)) for i, v in enumerate(values)],
        output_field=IntegerField(),
    )


def ordered_options():
    """Options in size, then grind order (4.3.6)."""
    return ProductOption.objects.order_by(
        _rank("weight_size", _WEIGHT_ORDER), _rank("grind_type", _GRIND_ORDER)
    )


def customer_products():
    """Every product a customer may see: STOPPED is hidden (FR-1, FR-6)."""
    return (
        Product.objects.exclude(sales_status=SalesStatus.STOPPED)
        .prefetch_related(Prefetch("options", queryset=ordered_options()))
        .order_by("-created_at", "-product_id")
    )


def _price_param(params, name):
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        value = int(raw)
    except ValueError:
        value = -1
    if value < 0:
        raise ValidationError({name: ["0 이상의 정수를 입력해 주세요."]})
    return value


def filter_customer_products(params):
    """Applies search and filters from the query string, all ANDed (4.3.2 ~ 4.3.5)."""
    qs = customer_products()

    search = (params.get("search") or "").strip()
    if search:
        qs = qs.filter(name__icontains=search)

    origin = params.get("origin")
    if origin:
        qs = qs.filter(origin=origin)

    min_price = _price_param(params, "min_price")
    max_price = _price_param(params, "max_price")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise ValidationError(
            {"min_price": ["최저 가격이 최고 가격보다 클 수 없습니다."]}
        )
    if min_price is not None:
        qs = qs.filter(base_price__gte=min_price)
    if max_price is not None:
        qs = qs.filter(base_price__lte=max_price)

    roast_level = params.get("roast_level")
    if roast_level:
        if roast_level not in RoastLevel.values:
            raise ValidationError({"roast_level": ["로스팅 정도를 확인해 주세요."]})
        qs = qs.filter(roast_level=roast_level)

    # Lowest option price; the base price when there is no option (4.3.1).
    return qs.annotate(
        lowest_price=F("base_price") + Coalesce(Min("options__extra_price"), Value(0))
    )
