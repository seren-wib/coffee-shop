"""Member cart (SDD 4.4), orders (SDD 4.5) and payments (SDD 4.6). Member-only by the default IsAuthenticated."""

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import StandardPagination
from orders import payments, services
from orders.models import Order, OrderStatus
from orders.serializers import (
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
        status_filter = request.query_params.get("status")
        if status_filter:  # empty means all (the “전체” tab)
            if status_filter not in OrderStatus.values:
                raise ValidationError({"status": ["알 수 없는 주문 상태입니다."]})
            orders = orders.filter(order_status=status_filter)
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
