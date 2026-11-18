"""Customer product views (SDD 4.3). Public routes (NFR-9)."""

from rest_framework import generics
from rest_framework.permissions import AllowAny

from products.queries import customer_products, filter_customer_products
from products.serializers import ProductDetailSerializer, ProductListSerializer


class ProductListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        return filter_customer_products(self.request.query_params)


class ProductDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductDetailSerializer
    queryset = customer_products()
