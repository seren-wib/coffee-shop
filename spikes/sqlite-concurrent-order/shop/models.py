"""Only the columns create_order touches (SDD 5.4).

No auth: a Member row stands in for the user, picked by the X-User-Id header.
"""
from django.db import models


class Member(models.Model):
    name = models.CharField(max_length=20)


class Product(models.Model):
    name = models.CharField(max_length=100)
    base_price = models.IntegerField()
    sales_status = models.CharField(max_length=10, default="ON_SALE")


class ProductOption(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="options")
    weight_size = models.CharField(max_length=10)
    grind_type = models.CharField(max_length=20)
    extra_price = models.IntegerField(default=0)
    stock_quantity = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(stock_quantity__gte=0), name="ck_stock_non_negative"
            )
        ]


class CartItem(models.Model):
    user = models.ForeignKey(Member, on_delete=models.CASCADE)
    option = models.ForeignKey(ProductOption, on_delete=models.CASCADE)
    quantity = models.IntegerField()


class Order(models.Model):
    order_id = models.CharField(max_length=16, primary_key=True)
    user = models.ForeignKey(Member, on_delete=models.CASCADE)
    order_status = models.CharField(max_length=16, default="PENDING")
    recipient_name = models.CharField(max_length=20)
    shipping_address = models.CharField(max_length=255)
    total_product_amt = models.IntegerField()
    shipping_fee = models.IntegerField()
    final_payment_amt = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    option = models.ForeignKey(ProductOption, on_delete=models.PROTECT)
    product_name = models.CharField(max_length=100)
    weight_size = models.CharField(max_length=10)
    grind_type = models.CharField(max_length=20)
    order_price = models.IntegerField()
    quantity = models.IntegerField()
