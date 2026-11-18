from django.urls import path

from products.admin_views import (
    AdminOptionCreateView,
    AdminOptionUpdateView,
    AdminProductDetailView,
    AdminProductListView,
    AdminResumeSalesView,
    AdminStopSalesView,
)
from products.views import ProductDetailView, ProductListView

urlpatterns = [
    path("products/", ProductListView.as_view(), name="product_list"),
    path("products/<int:pk>/", ProductDetailView.as_view(), name="product_detail"),
    path("admin/products/", AdminProductListView.as_view(), name="admin_product_list"),
    path(
        "admin/products/<int:pk>/",
        AdminProductDetailView.as_view(),
        name="admin_product_detail",
    ),
    path(
        "admin/products/<int:pk>/options/",
        AdminOptionCreateView.as_view(),
        name="admin_option_create",
    ),
    path(
        "admin/products/<int:pk>/options/<int:oid>/",
        AdminOptionUpdateView.as_view(),
        name="admin_option_update",
    ),
    path(
        "admin/products/<int:pk>/stop/",
        AdminStopSalesView.as_view(),
        name="admin_product_stop",
    ),
    path(
        "admin/products/<int:pk>/resume/",
        AdminResumeSalesView.as_view(),
        name="admin_product_resume",
    ),
]
