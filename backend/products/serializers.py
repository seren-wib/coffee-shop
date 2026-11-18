"""Customer product shapes (SDD 4.3.1, 4.3.6)."""

from rest_framework import serializers

from products.models import GrindType, Product, ProductOption, SalesStatus, WeightSize
from products.origins import ORIGINS


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


class AdminOptionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductOption
        fields = [
            "option_id",
            "weight_size",
            "grind_type",
            "extra_price",
            "stock_quantity",
        ]


class AdminProductListSerializer(serializers.ModelSerializer):
    option_count = serializers.IntegerField(read_only=True)
    total_stock = serializers.IntegerField(read_only=True)
    options = AdminOptionSummarySerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "product_id",
            "name",
            "origin",
            "roast_level",
            "base_price",
            "sales_status",
            "option_count",
            "total_stock",
            "options",
        ]


class AdminProductSerializer(serializers.ModelSerializer):
    """Create, update and the admin detail shape (4.7.2, 4.7.3, 4.7.12)."""

    options = OptionSerializer(many=True, read_only=True)
    base_price = serializers.IntegerField(min_value=0)
    image_url = serializers.CharField(
        max_length=500, required=False, allow_null=True, allow_blank=True
    )

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
            "created_at",
            "options",
        ]
        # The admin never picks a status; services switch it (DR-6, 4.7.3).
        read_only_fields = ["product_id", "sales_status", "created_at"]

    def validate_origin(self, value):
        if value not in ORIGINS:
            raise serializers.ValidationError("목록에 있는 원산지를 골라 주세요.")
        return value

    def validate_image_url(self, value):
        if not value:
            return None
        if not value.startswith("https://"):
            raise serializers.ValidationError("https:// 주소만 쓸 수 있습니다.")
        return value


class AdminOptionCreateSerializer(serializers.Serializer):
    weight_size = serializers.ChoiceField(choices=WeightSize.choices)
    grind_type = serializers.ChoiceField(choices=GrindType.choices)
    extra_price = serializers.IntegerField(min_value=0, default=0)
    stock_quantity = serializers.IntegerField(min_value=0, default=0)


class AdminOptionUpdateSerializer(serializers.Serializer):
    # Size and grind never change (4.7.5); unknown fields are ignored.
    extra_price = serializers.IntegerField(min_value=0, required=False)
    stock_quantity = serializers.IntegerField(min_value=0, required=False)
