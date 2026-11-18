"""Member cart (SDD 4.4). Every view is member-only by the default IsAuthenticated."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from orders import services
from orders.serializers import (
    CartAddSerializer,
    CartItemRefSerializer,
    CartQuantitySerializer,
    CartSerializer,
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
