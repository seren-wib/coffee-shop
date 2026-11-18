from django.db import models


class SalesStatus(models.TextChoices):
    ON_SALE = "ON_SALE", "On Sale"
    SOLD_OUT = "SOLD_OUT", "Sold Out"
    STOPPED = "STOPPED", "Stopped"


class GrindType(models.TextChoices):
    WHOLE_BEAN = "WHOLE_BEAN", "Whole Bean"
    HAND_DRIP = "HAND_DRIP", "Hand Drip"
    ESPRESSO = "ESPRESSO", "Espresso"


class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    origin = models.CharField(max_length=100)
    roast_level = models.CharField(max_length=50)
    base_price = models.PositiveIntegerField()
    tasting_notes = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    sales_status = models.CharField(
        max_length=20,
        choices=SalesStatus.choices,
        default=SalesStatus.ON_SALE,
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
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.origin})"

    def update_info(
        self,
        name=None,
        origin=None,
        roast_level=None,
        base_price=None,
        tasting_notes=None,
        description=None,
    ):
        if name is not None:
            self.name = name
        if origin is not None:
            self.origin = origin
        if roast_level is not None:
            self.roast_level = roast_level
        if base_price is not None:
            self.base_price = base_price
        if tasting_notes is not None:
            self.tasting_notes = tasting_notes
        if description is not None:
            self.description = description
        self.save()

    def change_sales_status(self, status: str):
        self.sales_status = status
        self.save(update_fields=["sales_status"])

    def calculate_price(self, option) -> int:
        return self.base_price + option.extra_price


class ProductOption(models.Model):
    option_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="options",
        db_column="product_id",
    )
    weight_size = models.CharField(max_length=50)  # e.g., '200g', '500g', '1kg'
    grind_type = models.CharField(
        max_length=50,
        choices=GrindType.choices,
        default=GrindType.WHOLE_BEAN,
    )
    extra_price = models.PositiveIntegerField(default=0)
    stock_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "product_options"
        unique_together = ("product", "weight_size", "grind_type")

    def __str__(self):
        return f"{self.product.name} - {self.weight_size} ({self.get_grind_type_display()})"

    def decrease_stock(self, quantity: int) -> bool:
        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            self.save(update_fields=["stock_quantity"])
            if self.stock_quantity == 0:
                # If all options out of stock, optionally update product status
                if not self.product.options.filter(stock_quantity__gt=0).exists():
                    self.product.change_sales_status(SalesStatus.SOLD_OUT)
            return True
        return False

    def increase_stock(self, quantity: int):
        self.stock_quantity += quantity
        self.save(update_fields=["stock_quantity"])
        if (
            self.product.sales_status == SalesStatus.SOLD_OUT
            and self.stock_quantity > 0
        ):
            self.product.change_sales_status(SalesStatus.ON_SALE)

    def is_available(self, quantity: int) -> bool:
        return self.stock_quantity >= quantity
