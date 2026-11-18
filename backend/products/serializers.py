"""Customer product shapes (SDD 4.3.1, 4.3.6)."""

from rest_framework import serializers

from products.models import Product, ProductOption, SalesStatus


class OptionSerializer(serializers.ModelSerializer):
    price = serializers.IntegerField(read_only=True)
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = ProductOption
        fields = [
            "option_id",
            "weight_size",
            "grind_type",
            "extra_price",
            "price",
            "stock_quantity",
            "is_available",
        ]

    def get_is_available(self, option):
        # DR-8: on sale and in stock.
        return (
            option.product.sales_status == SalesStatus.ON_SALE
            and option.stock_quantity > 0
        )


class ProductListSerializer(serializers.ModelSerializer):
    lowest_price = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "product_id",
            "name",
            "origin",
            "roast_level",
            "base_price",
            "lowest_price",
            "image_url",
            "sales_status",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "product_id",
            "name",
            "origin",
            "roast_level",
            "base_price",
            "tasting_notes",
            "description",
            "image_url",
            "sales_status",
            "options",
        ]
