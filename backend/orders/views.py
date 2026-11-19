"""Member cart (SDD 4.4), orders (SDD 4.5), payments (SDD 4.6) and admin orders (4.8).

Member views rely on the default IsAuthenticated; admin views add IsAdminRole.
"""

from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import StandardPagination
from common.permissions import IsAdminRole
from orders import payments, services
from orders.models import Order
from orders.serializers import (
    AdminOrderDetailSerializer,
    AdminOrderSummarySerializer,
    CancelRequestSerializer,
    CartAddSerializer,
    CartItemRefSerializer,
    CartQuantitySerializer,
    CartSerializer,
    ConfirmSerializer,
    FailSerializer,
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderSummarySerializer,
    ShipSerializer,
)


class CartView(APIView):
    def get(self, request):
        return Response(CartSerializer(services.cart_summary(request.user)).data)


class CartItemListView(APIView):
    def post(self, request):
        s = CartAddSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        item, created = services.add_to_cart(request.user, **s.validated_data)
        return Response(
            CartItemRefSerializer(item).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CartItemDetailView(APIView):
    def patch(self, request, pk):
        s = CartQuantitySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        item = services.change_cart_quantity(
            request.user, pk, s.validated_data["quantity"]
        )
        return Response(CartItemRefSerializer(item).data)

    def delete(self, request, pk):
        services.remove_cart_item(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderListView(APIView):
    def get(self, request):
        orders = (
            Order.objects.filter(user=request.user)
            .prefetch_related("items")
            .order_by("-created_at", "-order_id")
        )
        orders = services.filter_by_status(orders, request.query_params.get("status"))
        paginator = StandardPagination()
        page = paginator.paginate_queryset(orders, request, view=self)
        return paginator.get_paginated_response(
            OrderSummarySerializer(page, many=True).data
        )

    def post(self, request):
        s = OrderCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        order = services.create_order(request.user, **s.validated_data)
        return Response(
            OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED
        )


class OrderDetailView(APIView):
    def get(self, request, order_id):
        order = services.own_order(request.user, order_id)
        return Response(OrderDetailSerializer(order).data)


class OrderCancelView(APIView):
    def post(self, request, order_id):
        order = services.cancel_pending_order(request.user, order_id)
        return Response(OrderDetailSerializer(order).data)


class OrderCancelRequestView(APIView):
    def post(self, request, order_id):
        s = CancelRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        order = services.request_cancel(
            request.user, order_id, s.validated_data["reason"]
        )
        return Response(OrderDetailSerializer(order).data)


class PaymentStartView(APIView):
    def post(self, request, order_id):
        payment = payments.start_payment(request.user, order_id)
        return Response(
            {
                "payment_id": payment.payment_id,
                "pg_order_id": payment.pg_order_id,
                "amount": payment.paid_amount,
                "order_name": payments.order_name(payment.order),
                "customer_name": request.user.user_name,
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentConfirmView(APIView):
    def post(self, request):
        s = ConfirmSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        order = payments.confirm_payment(
            request.user,
            payment_key=data["paymentKey"],
            pg_order_id=data["orderId"],
            amount=data["amount"],
        )
        return Response(
            {
                "order_id": order.order_id,
                "status": order.order_status,
                "final_payment_amt": order.final_payment_amt,
            }
        )


class PaymentFailView(APIView):
    def post(self, request):
        s = FailSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        payments.fail_payment(
            request.user,
            pg_order_id=data.get("orderId"),
            code=data.get("code", ""),
            message=data.get("message", ""),
        )
        return Response({})


class AdminView(APIView):
    """Every /api/admin/orders/ view: token plus DB role ADMIN (NFR-10)."""

    permission_classes = [IsAuthenticated, IsAdminRole]


def _admin_detail(order):
    return Response(AdminOrderDetailSerializer(order).data)


class AdminOrderListView(AdminView):
    def get(self, request):
        orders = Order.objects.select_related("user").order_by(
            "-created_at", "-order_id"
        )
        orders = services.filter_by_status(orders, request.query_params.get("status"))
        search = request.query_params.get("search", "").strip()
        if search:
            orders = orders.filter(
                Q(order_id__icontains=search) | Q(user__email__icontains=search)
            )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(orders, request, view=self)
        return paginator.get_paginated_response(
            AdminOrderSummarySerializer(page, many=True).data
        )


class AdminOrderDetailView(AdminView):
    def get(self, request, order_id):
        return _admin_detail(services.admin_order(order_id))


class AdminPrepareView(AdminView):
    def post(self, request, order_id):
        return _admin_detail(services.prepare(order_id))


class AdminShipView(AdminView):
    def post(self, request, order_id):
        s = ShipSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return _admin_detail(services.ship(order_id, **s.validated_data))


class AdminDeliverView(AdminView):
    def post(self, request, order_id):
        return _admin_detail(services.deliver(order_id))


class AdminCancelApproveView(AdminView):
    def post(self, request, order_id):
        return _admin_detail(services.approve_cancel(order_id))


class AdminCancelRejectView(AdminView):
    def post(self, request, order_id):
        return _admin_detail(services.reject_cancel(order_id))
