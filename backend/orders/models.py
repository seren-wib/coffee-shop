from django.db import models, transaction
from django.utils import timezone


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PAID = "PAID", "Paid"
    PREPARING = "PREPARING", "Preparing"
    SHIPPED = "SHIPPED", "Shipped"
    DELIVERED = "DELIVERED", "Delivered"
    CANCEL_REQUESTED = "CANCEL_REQUESTED", "Cancel Requested"
    CANCELLED = "CANCELLED", "Cancelled"


class PaymentMethod(models.TextChoices):
    CARD = "CARD", "Credit/Debit Card"
    EASY_PAY = "EASY_PAY", "Easy Pay"
    TRANSFER = "TRANSFER", "Bank Transfer"


class PaymentStatus(models.TextChoices):
    READY = "READY", "Ready"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class CartItem(models.Model):
    cart_item_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="cart_items",
        db_column="user_id",
    )
    option = models.ForeignKey(
        "products.ProductOption",
        on_delete=models.CASCADE,
        related_name="cart_items",
        db_column="option_id",
    )
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cart_items"
        unique_together = ("user", "option")
        indexes = [
            models.Index(fields=["user"], name="idx_cart_items_user_id"),
        ]

    def __str__(self):
        return f"Cart #{self.cart_item_id} (User {self.user_id}) - {self.option} x {self.quantity}"

    def update_quantity(self, quantity: int):
        if quantity > 0:
            self.quantity = quantity
            self.save(update_fields=["quantity"])

    def get_subtotal(self) -> int:
        unit_price = self.option.product.base_price + self.option.extra_price
        return unit_price * self.quantity


class Order(models.Model):
    order_id = models.CharField(primary_key=True, max_length=50)  # e.g., 'ORD-2026-X'
    user = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="orders",
        db_column="user_id",
    )
    order_status = models.CharField(
        max_length=30,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
    )
    total_product_amt = models.PositiveIntegerField()
    shipping_fee = models.PositiveIntegerField(default=0)
    final_payment_amt = models.PositiveIntegerField()
    recipient_name = models.CharField(max_length=100)
    recipient_phone = models.CharField(max_length=20)
    shipping_address = models.CharField(max_length=255)
    courier_name = models.CharField(max_length=50, blank=True, null=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    ordered_at = models.DateTimeField(auto_now_add=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "orders"
        indexes = [
            models.Index(fields=["user"], name="idx_orders_user_id"),
            models.Index(
                fields=["order_status", "-ordered_at"],
                name="idx_orders_status_ordered_at",
            ),
            models.Index(fields=["tracking_number"], name="idx_orders_tracking"),
        ]
        ordering = ["-ordered_at"]

    def __str__(self):
        return f"Order {self.order_id} ({self.get_order_status_display()}) - {self.final_payment_amt:,} KRW"

    @classmethod
    @transaction.atomic
    def create_order(
        cls,
        user,
        order_id,
        recipient_name,
        recipient_phone,
        shipping_address,
        cart_items,
        shipping_fee=3000,
    ):
        total_product_amt = 0
        order_item_instances = []

        for item in cart_items:
            unit_price = item.option.product.base_price + item.option.extra_price
            total_product_amt += unit_price * item.quantity

            if not item.option.decrease_stock(item.quantity):
                raise ValueError(f"Insufficient stock for {item.option}")

            order_item_instances.append(
                OrderItem(
                    option=item.option,
                    product_name=item.option.product.name,
                    weight_size=item.option.weight_size,
                    grind_type=item.option.get_grind_type_display(),
                    order_price=unit_price,
                    quantity=item.quantity,
                )
            )

        final_amt = total_product_amt + shipping_fee
        order = cls.objects.create(
            order_id=order_id,
            user=user,
            total_product_amt=total_product_amt,
            shipping_fee=shipping_fee,
            final_payment_amt=final_amt,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            shipping_address=shipping_address,
            order_status=OrderStatus.PENDING,
        )

        for oi in order_item_instances:
            oi.order = order
            oi.save()

        # Remove checked cart items
        for item in cart_items:
            item.delete()

        return order

    def request_cancellation(self) -> bool:
        """Member requests order cancellation."""
        if self.order_status == OrderStatus.PENDING:
            with transaction.atomic():
                self.order_status = OrderStatus.CANCELLED
                self.save(update_fields=["order_status"])
                for item in self.items.all():
                    item.option.increase_stock(item.quantity)
            return True
        elif self.order_status in [OrderStatus.PAID, OrderStatus.PREPARING]:
            self.order_status = OrderStatus.CANCEL_REQUESTED
            self.save(update_fields=["order_status"])
            return True
        return False

    def process_cancellation(self, approved: bool) -> bool:
        """Administrator processes cancellation request."""
        if self.order_status != OrderStatus.CANCEL_REQUESTED:
            return False

        with transaction.atomic():
            if approved:
                self.order_status = OrderStatus.CANCELLED
                self.save(update_fields=["order_status"])
                # Rollback stock
                for item in self.items.all():
                    item.option.increase_stock(item.quantity)
                # Refund payments
                for payment in self.payments.filter(
                    payment_status=PaymentStatus.SUCCESS
                ):
                    payment.cancel_payment("Admin approved cancellation request")
            else:
                self.order_status = OrderStatus.PREPARING
                self.save(update_fields=["order_status"])
        return True

    def register_tracking(self, courier: str, tracking_no: str):
        """Admin registers courier shipment tracking and marks order as SHIPPED."""
        self.courier_name = courier
        self.tracking_number = tracking_no
        self.order_status = OrderStatus.SHIPPED
        self.shipped_at = timezone.now()
        self.save(
            update_fields=[
                "courier_name",
                "tracking_number",
                "order_status",
                "shipped_at",
            ]
        )

    def mark_as_delivered(self):
        """Marks order as DELIVERED upon completed shipment."""
        self.order_status = OrderStatus.DELIVERED
        self.delivered_at = timezone.now()
        self.save(update_fields=["order_status", "delivered_at"])

    def update_status(self, new_status: str):
        self.order_status = new_status
        self.save(update_fields=["order_status"])

    def calculate_total(self) -> int:
        return self.total_product_amt + self.shipping_fee


class OrderItem(models.Model):
    order_item_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items", db_column="order_id"
    )
    option = models.ForeignKey(
        "products.ProductOption", on_delete=models.PROTECT, db_column="option_id"
    )
    product_name = models.CharField(max_length=200)
    weight_size = models.CharField(max_length=50)
    grind_type = models.CharField(max_length=50)
    order_price = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()

    class Meta:
        db_table = "order_items"
        indexes = [
            models.Index(fields=["order"], name="idx_order_items_order_id"),
        ]

    def __str__(self):
        return f"{self.product_name} ({self.weight_size}, {self.grind_type}) x {self.quantity}"

    def calculate_subtotal(self) -> int:
        return self.order_price * self.quantity


class Payment(models.Model):
    payment_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="payments", db_column="order_id"
    )
    pg_provider = models.CharField(max_length=50)
    pg_tid = models.CharField(max_length=100, unique=True, null=True, blank=True)
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.READY,
    )
    paid_amount = models.PositiveIntegerField()
    failure_reason = models.TextField(blank=True, null=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payments"
        indexes = [
            models.Index(fields=["order"], name="idx_payments_order_id"),
        ]

    def __str__(self):
        return f"Payment #{self.payment_id} for {self.order_id} - {self.get_payment_status_display()}"

    def process_payment(self, pg_tid: str) -> bool:
        self.pg_tid = pg_tid
        self.payment_status = PaymentStatus.SUCCESS
        self.approved_at = timezone.now()
        self.save(update_fields=["pg_tid", "payment_status", "approved_at"])
        self.order.update_status(OrderStatus.PAID)
        return True

    def cancel_payment(self, reason: str) -> bool:
        self.payment_status = PaymentStatus.CANCELLED
        self.failure_reason = reason
        self.save(update_fields=["payment_status", "failure_reason"])
        return True
