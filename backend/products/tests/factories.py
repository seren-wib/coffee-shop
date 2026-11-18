"""Test data builders for products (STP 1.2)."""

from itertools import count

from products.models import GrindType, Product, ProductOption, RoastLevel, WeightSize

_seq = count(1)


def make_product(options=None, **fields):
    """options: dicts of ProductOption fields; default is one 200G whole bean, stock 10."""
    n = next(_seq)
    fields.setdefault("name", f"원두 {n}")
    fields.setdefault("origin", "에티오피아")
    fields.setdefault("roast_level", RoastLevel.LIGHT)
    fields.setdefault("base_price", 18000)
    product = Product.objects.create(**fields)
    for opt in options if options is not None else [{}]:
        opt = dict(opt)
        opt.setdefault("weight_size", WeightSize.G200)
        opt.setdefault("grind_type", GrindType.WHOLE_BEAN)
        opt.setdefault("stock_quantity", 10)
        ProductOption.objects.create(product=product, **opt)
    return product
