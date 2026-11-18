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
    path("orders/", views.OrderListView.as_view(), name="orders"),
    path(
        "orders/<str:order_id>/", views.OrderDetailView.as_view(), name="order_detail"
    ),
    path(
        "orders/<str:order_id>/cancel/",
        views.OrderCancelView.as_view(),
        name="order_cancel",
    ),
    path(
        "orders/<str:order_id>/cancel-request/",
        views.OrderCancelRequestView.as_view(),
        name="order_cancel_request",
    ),
]
