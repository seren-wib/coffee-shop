"""Request and response shapes for cart and orders (SDD 4.4, 4.5)."""

from rest_framework import serializers

from orders import services
from orders.models import CartItem


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
