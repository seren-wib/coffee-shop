"""Cart, orders, order items and payments (SDD 6.5 ~ 6.8).

Status columns change only through conditional UPDATEs in services (SDD 4.0, 6.9),
so the models have no methods that change status.
"""

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PAID = "PAID", "Paid"
    PREPARING = "PREPARING", "Preparing"
    SHIPPED = "SHIPPED", "Shipped"
    DELIVERED = "DELIVERED", "Delivered"
    CANCEL_REQUESTED = "CANCEL_REQUESTED", "Cancel requested"
    CANCELLED = "CANCELLED", "Cancelled"


class PaymentStatus(models.TextChoices):
    READY = "READY", "Ready"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class PaymentMethod(models.TextChoices):
    CARD = "CARD", "Card"
    EASY_PAY = "EASY_PAY", "Easy pay"
    TRANSFER = "TRANSFER", "Transfer"
    OTHER = "OTHER", "Other"


class Courier(models.TextChoices):
    CJ = "CJ", "CJ대한통운"
    HANJIN = "HANJIN", "한진택배"
    LOTTE = "LOTTE", "롯데택배"
    EPOST = "EPOST", "우체국택배"
    LOGEN = "LOGEN", "로젠택배"


class CartItem(models.Model):
    cart_item_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart_items"
    )
    option = models.ForeignKey(
        "products.ProductOption", on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cart_items"
        indexes = [models.Index(fields=["user"], name="idx_cart_items_user_id")]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "option"], name="uq_cart_items_user_option"
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0), name="ck_cart_items_quantity"
            ),
        ]


class Order(models.Model):
    order_id = models.CharField(max_length=16, primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    order_status = models.CharField(
        max_length=16, choices=OrderStatus.choices, default=OrderStatus.PENDING
    )
    status_before_cancel = models.CharField(
        max_length=16, choices=OrderStatus.choices, null=True, blank=True
    )
    cancel_reason = models.TextField(null=True, blank=True)
    total_product_amt = models.IntegerField()
    shipping_fee = models.IntegerField()
    final_payment_amt = models.IntegerField()
    recipient_name = models.CharField(max_length=100)
    recipient_phone = models.CharField(max_length=20)
    shipping_address = models.CharField(max_length=400)
    courier_code = models.CharField(
        max_length=10, choices=Courier.choices, null=True, blank=True
    )
    tracking_number = models.CharField(max_length=30, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "orders"
        indexes = [
            models.Index(fields=["user"], name="idx_orders_user_id"),
            models.Index(fields=["tracking_number"], name="idx_orders_tracking"),
            models.Index(
                fields=["order_status", "-created_at"],
                name="idx_orders_status_created",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(order_status__in=OrderStatus.values),
                name="ck_orders_status",
            ),
            models.CheckConstraint(
                condition=Q(status_before_cancel__isnull=True)
                | Q(
                    status_before_cancel__in=[
                        OrderStatus.PAID,
                        OrderStatus.PREPARING,
                    ]
                ),
                name="ck_orders_status_before_cancel",
            ),
            models.CheckConstraint(
                condition=Q(total_product_amt__gte=0), name="ck_orders_total"
            ),
            models.CheckConstraint(
                condition=Q(shipping_fee__in=[0, 3000]), name="ck_orders_shipping_fee"
            ),
            models.CheckConstraint(
                condition=Q(
                    final_payment_amt=F("total_product_amt") + F("shipping_fee")
                ),
                name="ck_orders_final_amount",
            ),
            models.CheckConstraint(
                condition=Q(courier_code__isnull=True)
                | Q(courier_code__in=Courier.values),
                name="ck_orders_courier",
            ),
            models.CheckConstraint(
                condition=~Q(
                    order_status__in=[OrderStatus.SHIPPED, OrderStatus.DELIVERED]
                )
                | Q(
                    courier_code__isnull=False,
                    tracking_number__isnull=False,
                    shipped_at__isnull=False,
                ),
                name="ck_orders_shipped_fields",
            ),
            # Rejecting a cancel request restores this value (FR-51).
            models.CheckConstraint(
                condition=~Q(order_status=OrderStatus.CANCEL_REQUESTED)
                | Q(status_before_cancel__isnull=False),
                name="ck_orders_cancel_request_previous",
            ),
        ]

    def __str__(self):
        return self.order_id


class OrderItem(models.Model):
    order_item_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    option = models.ForeignKey(
        "products.ProductOption", on_delete=models.PROTECT, related_name="order_items"
    )
    product_name = models.CharField(max_length=200)
    weight_size = models.CharField(max_length=4)
    grind_type = models.CharField(max_length=12)
    order_price = models.IntegerField()
    quantity = models.IntegerField()

    class Meta:
        db_table = "order_items"
        indexes = [models.Index(fields=["order"], name="idx_order_items_order_id")]
        constraints = [
            models.CheckConstraint(
                condition=Q(order_price__gte=0), name="ck_order_items_price"
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0), name="ck_order_items_quantity"
            ),
        ]


class Payment(models.Model):
    payment_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments")
    pg_provider = models.CharField(max_length=10, default="TOSS")
    pg_order_id = models.CharField(max_length=64, unique=True)
    pg_tid = models.CharField(max_length=200, null=True, blank=True, unique=True)
    payment_method = models.CharField(
        max_length=10, choices=PaymentMethod.choices, null=True, blank=True
    )
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.READY
    )
    paid_amount = models.IntegerField()
    failure_reason = models.CharField(max_length=500, null=True, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payments"
        indexes = [models.Index(fields=["order"], name="idx_payments_order_id")]
        constraints = [
            models.UniqueConstraint(
                fields=["order"],
                condition=Q(payment_status=PaymentStatus.SUCCESS),
                name="uq_payments_order_success",
            ),
            models.CheckConstraint(
                condition=Q(payment_status__in=PaymentStatus.values),
                name="ck_payments_status",
            ),
            models.CheckConstraint(
                condition=Q(paid_amount__gte=0), name="ck_payments_amount"
            ),
        ]
