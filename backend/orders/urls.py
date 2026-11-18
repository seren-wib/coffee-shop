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
    path(
        "orders/<str:order_id>/payments/",
        views.PaymentStartView.as_view(),
        name="payment_start",
    ),
    path(
        "payments/confirm/", views.PaymentConfirmView.as_view(), name="payment_confirm"
    ),
    path("payments/fail/", views.PaymentFailView.as_view(), name="payment_fail"),
    path("admin/orders/", views.AdminOrderListView.as_view(), name="admin_orders"),
    path(
        "admin/orders/<str:order_id>/",
        views.AdminOrderDetailView.as_view(),
        name="admin_order_detail",
    ),
    path(
        "admin/orders/<str:order_id>/prepare/",
        views.AdminPrepareView.as_view(),
        name="admin_order_prepare",
    ),
    path(
        "admin/orders/<str:order_id>/ship/",
        views.AdminShipView.as_view(),
        name="admin_order_ship",
    ),
    path(
        "admin/orders/<str:order_id>/deliver/",
        views.AdminDeliverView.as_view(),
        name="admin_order_deliver",
    ),
    path(
        "admin/orders/<str:order_id>/cancel-approve/",
        views.AdminCancelApproveView.as_view(),
        name="admin_order_cancel_approve",
    ),
    path(
        "admin/orders/<str:order_id>/cancel-reject/",
        views.AdminCancelRejectView.as_view(),
        name="admin_order_cancel_reject",
    ),
]
