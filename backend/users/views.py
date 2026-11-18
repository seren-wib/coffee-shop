"""Sign-up, login, token refresh, my profile (SDD 4.1) and addresses (SDD 4.2)."""

from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from common.exceptions import DomainError
from users import services
from users.models import UserAddress
from users.serializers import (
    AddressSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    ProfileSerializer,
    RegisterSerializer,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("privacy_agreed")
        user = services.register_member(**data)
        return Response(ProfileSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except (AuthenticationFailed, TokenError):
            # Same body for unknown email, wrong password and inactive account (NFR-7).
            raise DomainError(
                "INVALID_CREDENTIALS",
                "이메일 또는 비밀번호가 올바르지 않습니다.",
                status.HTTP_401_UNAUTHORIZED,
            )


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except (InvalidToken, TokenError):
            raise DomainError(
                "INVALID_TOKEN",
                "로그인이 만료되었습니다. 다시 로그인해 주세요.",
                status.HTTP_401_UNAUTHORIZED,
            )


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    http_method_names = ["get", "patch"]

    def get_object(self):
        return self.request.user


class PasswordChangeView(APIView):
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        services.change_password(
            request.user, serializer.validated_data["new_password"]
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AddressListView(APIView):
    def get(self, request):
        addresses = UserAddress.objects.filter(user=request.user).order_by(
            "-is_default", "-created_at"
        )
        return Response(AddressSerializer(addresses, many=True).data)

    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address = services.create_address(request.user, **serializer.validated_data)
        return Response(AddressSerializer(address).data, status=status.HTTP_201_CREATED)


class AddressDetailView(APIView):
    def patch(self, request, pk):
        serializer = AddressSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("is_default", None)
        address = services.update_address(request.user, pk, **data)
        return Response(AddressSerializer(address).data)

    def delete(self, request, pk):
        services.delete_address(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AddressDefaultView(APIView):
    def post(self, request, pk):
        address = services.set_default_address(request.user, pk)
        return Response(AddressSerializer(address).data)
