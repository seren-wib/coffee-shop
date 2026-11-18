"""Beans and their options (SDD 5.3, 5.4). Stock and sales status change only in services."""

from django.db import models
from django.db.models import Q


class RoastLevel(models.TextChoices):
    LIGHT = "LIGHT", "Light"
    MEDIUM = "MEDIUM", "Medium"
    DARK = "DARK", "Dark"


class WeightSize(models.TextChoices):
    G200 = "200G", "200g"
    G500 = "500G", "500g"
    KG1 = "1KG", "1kg"


class GrindType(models.TextChoices):
    WHOLE_BEAN = "WHOLE_BEAN", "Whole bean"
    HAND_DRIP = "HAND_DRIP", "Hand drip"
    ESPRESSO = "ESPRESSO", "Espresso"


class SalesStatus(models.TextChoices):
    ON_SALE = "ON_SALE", "On sale"
    SOLD_OUT = "SOLD_OUT", "Sold out"
    STOPPED = "STOPPED", "Stopped"


class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    origin = models.CharField(max_length=100)
    roast_level = models.CharField(max_length=10, choices=RoastLevel.choices)
    base_price = models.IntegerField()
    tasting_notes = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    image_url = models.CharField(max_length=500, null=True, blank=True)
    sales_status = models.CharField(
        max_length=10, choices=SalesStatus.choices, default=SalesStatus.ON_SALE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "products"
        indexes = [
            models.Index(fields=["name"], name="idx_products_name"),
            models.Index(
                fields=["origin", "roast_level", "base_price"],
                name="idx_products_filter",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(roast_level__in=RoastLevel.values),
                name="ck_products_roast_level",
            ),
            models.CheckConstraint(
                condition=Q(base_price__gte=0), name="ck_products_base_price"
            ),
            models.CheckConstraint(
                condition=Q(sales_status__in=SalesStatus.values),
                name="ck_products_sales_status",
            ),
        ]

    def __str__(self):
        return self.name


class ProductOption(models.Model):
    option_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="options"
    )
    weight_size = models.CharField(max_length=4, choices=WeightSize.choices)
    grind_type = models.CharField(max_length=12, choices=GrindType.choices)
    extra_price = models.IntegerField(default=0)
    stock_quantity = models.IntegerField(default=0)

    class Meta:
        db_table = "product_options"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "weight_size", "grind_type"],
                name="uq_product_options_combo",
            ),
            models.CheckConstraint(
                condition=Q(weight_size__in=WeightSize.values),
                name="ck_product_options_weight_size",
            ),
            models.CheckConstraint(
                condition=Q(grind_type__in=GrindType.values),
                name="ck_product_options_grind_type",
            ),
            models.CheckConstraint(
                condition=Q(extra_price__gte=0), name="ck_product_options_extra_price"
            ),
            models.CheckConstraint(
                condition=Q(stock_quantity__gte=0), name="ck_product_options_stock"
            ),
        ]

    def __str__(self):
        return f"{self.product.name} {self.weight_size} {self.grind_type}"

    @property
    def price(self):
        # Not stored: changing the base price changes every option price (DR-4).
        return self.product.base_price + self.extra_price
