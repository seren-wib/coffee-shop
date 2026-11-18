from django.urls import path

from orders import views

urlpatterns = [
    path("cart/", views.CartView.as_view(), name="cart"),
    path("cart/items/", views.CartItemListView.as_view(), name="cart_items"),
    path(
        "cart/items/<int:pk>/",
        views.CartItemDetailView.as_view(),
        name="cart_item_detail",
    ),
]
