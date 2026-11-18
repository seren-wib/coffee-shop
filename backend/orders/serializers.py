"""Request and response shapes for cart and orders (SDD 4.4, 4.5)."""

from rest_framework import serializers

from orders import couriers, services
from orders.models import (
    CartItem,
    Courier,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentStatus,
)
from users.serializers import phone_validator, zipcode_validator


class CartAddSerializer(serializers.Serializer):
    option_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class CartQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class CartItemRefSerializer(serializers.ModelSerializer):
    option_id = serializers.IntegerField(source="option.option_id")

    class Meta:
        model = CartItem
        fields = ["cart_item_id", "option_id", "quantity"]


class CartLineSerializer(serializers.Serializer):
    cart_item_id = serializers.IntegerField()
    option_id = serializers.IntegerField(source="option.option_id")
    product_id = serializers.IntegerField(source="option.product.product_id")
    product_name = serializers.CharField(source="option.product.name")
    image_url = serializers.CharField(source="option.product.image_url")
    weight_size = serializers.CharField(source="option.weight_size")
    grind_type = serializers.CharField(source="option.grind_type")
    price = serializers.IntegerField(source="option.price")
    quantity = serializers.IntegerField()
    subtotal = serializers.SerializerMethodField()
    stock_quantity = serializers.IntegerField(source="option.stock_quantity")
    is_available = serializers.SerializerMethodField()

    def get_subtotal(self, item):
        return item.option.price * item.quantity

    def get_is_available(self, item):
        return services.is_available(item)


class CartSerializer(serializers.Serializer):
    items = CartLineSerializer(many=True)
    product_amount = serializers.IntegerField()
    shipping_fee = serializers.IntegerField()
    total_amount = serializers.IntegerField()
    can_order = serializers.BooleanField()


class OrderAddressSerializer(serializers.Serializer):
    recipient_name = serializers.CharField(max_length=100)
    # Same rules as the address book (users/serializers.py).
    recipient_phone = serializers.CharField(max_length=20, validators=[phone_validator])
    zipcode = serializers.CharField(max_length=10, validators=[zipcode_validator])
    base_address = serializers.CharField(max_length=255)
    detail_address = serializers.CharField(
        max_length=255, required=False, allow_blank=True, allow_null=True
    )


class OrderCreateSerializer(serializers.Serializer):
    """Exactly one of a saved address_id or a new address (SDD 4.5.3)."""

    address_id = serializers.IntegerField(required=False)
    address = OrderAddressSerializer(required=False)

    def validate(self, attrs):
        if ("address_id" in attrs) == ("address" in attrs):
            raise serializers.ValidationError(
                {"address": ["배송지를 하나 선택하거나 입력해 주세요."]}
            )
        return attrs


class CancelRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class OrderItemLineSerializer(serializers.ModelSerializer):
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "product_name",
            "weight_size",
            "grind_type",
            "order_price",
            "quantity",
            "subtotal",
        ]

    def get_subtotal(self, item):
        return item.order_price * item.quantity


class PaymentLineSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="payment_status")
    method = serializers.CharField(source="payment_method")

    class Meta:
        model = Payment
        fields = [
            "payment_id",
            "status",
            "method",
            "paid_amount",
            "failure_reason",
            "approved_at",
        ]


SHIPPING_STATUSES = (OrderStatus.SHIPPED, OrderStatus.DELIVERED)


class OrderDetailSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="order_status")
    items = serializers.SerializerMethodField()
    payments = serializers.SerializerMethodField()
    courier_name = serializers.SerializerMethodField()
    tracking_number = serializers.SerializerMethodField()
    tracking_url = serializers.SerializerMethodField()
    shipped_at = serializers.SerializerMethodField()
    delivered_at = serializers.SerializerMethodField()
    can_pay = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    can_request_cancel = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "order_id",
            "status",
            "created_at",
            "items",
            "total_product_amt",
            "shipping_fee",
            "final_payment_amt",
            "recipient_name",
            "recipient_phone",
            "shipping_address",
            "payments",
            "courier_name",
            "tracking_number",
            "tracking_url",
            "shipped_at",
            "delivered_at",
            "cancel_reason",
            "can_pay",
            "can_cancel",
            "can_request_cancel",
        ]

    def to_representation(self, order):
        # Load payments once; get_payments and get_can_pay both read them.
        order._payment_rows = list(order.payments.order_by("payment_id"))
        return super().to_representation(order)

    def _shipping(self, order):
        return order.order_status in SHIPPING_STATUSES

    def get_items(self, order):
        items = order.items.order_by("order_item_id")
        return OrderItemLineSerializer(items, many=True).data

    def get_payments(self, order):
        return PaymentLineSerializer(order._payment_rows, many=True).data

    def get_courier_name(self, order):
        return (
            couriers.courier_name(order.courier_code) if self._shipping(order) else None
        )

    def get_tracking_number(self, order):
        return order.tracking_number if self._shipping(order) else None

    def get_tracking_url(self, order):
        if not self._shipping(order):
            return None
        return couriers.tracking_url(order.courier_code, order.tracking_number)

    def _shipping_time(self, order, value):
        if value is None or not self._shipping(order):
            return None
        return serializers.DateTimeField().to_representation(value)

    def get_shipped_at(self, order):
        return self._shipping_time(order, order.shipped_at)

    def get_delivered_at(self, order):
        return self._shipping_time(order, order.delivered_at)

    def get_can_pay(self, order):
        return order.order_status == OrderStatus.PENDING and not any(
            p.payment_status == PaymentStatus.SUCCESS for p in order._payment_rows
        )

    def get_can_cancel(self, order):
        return order.order_status == OrderStatus.PENDING

    def get_can_request_cancel(self, order):
        return order.order_status in (OrderStatus.PAID, OrderStatus.PREPARING)


class OrderSummarySerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="order_status")
    item_count = serializers.SerializerMethodField()
    first_item_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "order_id",
            "created_at",
            "final_payment_amt",
            "status",
            "item_count",
            "first_item_name",
        ]

    def get_item_count(self, order):
        return len(order.items.all())

    def get_first_item_name(self, order):
        items = sorted(order.items.all(), key=lambda i: i.order_item_id)
        return items[0].product_name if items else None


class ConfirmSerializer(serializers.Serializer):
    # Toss's own names, passed through from successUrl (SDD 7.1).
    paymentKey = serializers.CharField(max_length=200)
    orderId = serializers.CharField(max_length=64)
    amount = serializers.IntegerField(min_value=0)


class FailSerializer(serializers.Serializer):
    orderId = serializers.CharField(max_length=64, required=False, allow_blank=True)
    code = serializers.CharField(max_length=100, required=False, allow_blank=True)
    message = serializers.CharField(max_length=400, required=False, allow_blank=True)


class ShipSerializer(serializers.Serializer):
    courier_code = serializers.ChoiceField(
        choices=Courier.choices,
        error_messages={"invalid_choice": "목록에 있는 택배사를 골라 주세요."},
    )
    tracking_number = serializers.RegexField(
        r"^[0-9-]{1,30}$",
        error_messages={"invalid": "송장번호는 숫자와 -만, 30자 이하로 입력해 주세요."},
    )


class AdminOrderSummarySerializer(serializers.ModelSerializer):
    member_email = serializers.CharField(source="user.email")
    member_name = serializers.CharField(source="user.user_name")
    status = serializers.CharField(source="order_status")

    class Meta:
        model = Order
        fields = [
            "order_id",
            "created_at",
            "member_email",
            "member_name",
            "final_payment_amt",
            "status",
        ]


class AdminPaymentLineSerializer(PaymentLineSerializer):
    pg_tid = serializers.SerializerMethodField()

    class Meta(PaymentLineSerializer.Meta):
        fields = PaymentLineSerializer.Meta.fields + [
            "pg_order_id",
            "pg_tid",
            "requested_at",
        ]

    def get_pg_tid(self, payment):
        # The screen shows only the last 8 characters of a paymentKey (SDD 4.8.3, 8.5).
        return payment.pg_tid[-8:] if payment.pg_tid else None


ALLOWED_ACTIONS = {
    OrderStatus.PAID: ["prepare"],
    OrderStatus.PREPARING: ["ship"],
    OrderStatus.SHIPPED: ["deliver"],
    OrderStatus.CANCEL_REQUESTED: ["cancel_approve", "cancel_reject"],
}


class AdminOrderDetailSerializer(OrderDetailSerializer):
    member = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField()

    class Meta(OrderDetailSerializer.Meta):
        fields = OrderDetailSerializer.Meta.fields + [
            "member",
            "status_before_cancel",
            "allowed_actions",
        ]

    def get_member(self, order):
        user = order.user
        return {
            "user_id": user.user_id,
            "email": user.email,
            "user_name": user.user_name,
            "phone_number": user.phone_number,
        }

    def get_payments(self, order):
        return AdminPaymentLineSerializer(order._payment_rows, many=True).data

    def get_allowed_actions(self, order):
        return ALLOWED_ACTIONS.get(order.order_status, [])
