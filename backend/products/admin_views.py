"""Admin product views (SDD 4.7). Every route needs an ADMIN token (NFR-10)."""

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdminRole
from products import services
from products.queries import admin_product_detail, admin_products
from products.serializers import (
    AdminOptionCreateSerializer,
    AdminOptionUpdateSerializer,
    AdminProductListSerializer,
    AdminProductSerializer,
)

ADMIN = [IsAuthenticated, IsAdminRole]


def _detail(product_id, status_code=status.HTTP_200_OK):
    product = get_object_or_404(admin_product_detail(), pk=product_id)
    return Response(AdminProductSerializer(product).data, status=status_code)


class AdminProductListView(generics.ListCreateAPIView):
    permission_classes = ADMIN

    def get_queryset(self):
        return admin_products(self.request.query_params)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminProductSerializer
        return AdminProductListSerializer

    def create(self, request, *args, **kwargs):
        serializer = AdminProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return _detail(product.pk, status.HTTP_201_CREATED)


class AdminProductDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = ADMIN
    serializer_class = AdminProductSerializer
    http_method_names = ["get", "patch", "options"]

    def get_queryset(self):
        return admin_product_detail()

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        super().update(request, *args, **kwargs)
        return _detail(kwargs["pk"])


class AdminOptionCreateView(APIView):
    permission_classes = ADMIN

    def post(self, request, pk):
        serializer = AdminOptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.add_option(pk, **serializer.validated_data)
        return _detail(pk, status.HTTP_201_CREATED)


class AdminOptionUpdateView(APIView):
    permission_classes = ADMIN

    def patch(self, request, pk, oid):
        serializer = AdminOptionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.update_option(pk, oid, **serializer.validated_data)
        return _detail(pk)


class AdminStopSalesView(APIView):
    permission_classes = ADMIN

    def post(self, request, pk):
        services.stop_sales(pk)
        return _detail(pk)


class AdminResumeSalesView(APIView):
    permission_classes = ADMIN

    def post(self, request, pk):
        services.resume_sales(pk)
        return _detail(pk)
