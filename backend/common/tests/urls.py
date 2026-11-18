"""URLconf for common API tests: the real routes plus views that raise on purpose."""

from django.urls import path
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from common.exceptions import DomainError
from common.permissions import IsAdminRole
from config.urls import urlpatterns as real_urlpatterns


class _NameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=3)


@api_view(["POST"])
@permission_classes([AllowAny])
def raise_validation(request):
    s = _NameSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    return Response(s.validated_data)


@api_view(["GET"])
@permission_classes([AllowAny])
def raise_domain(request):
    raise DomainError(
        "OUT_OF_STOCK", "재고가 부족합니다.", 409, details={"cart_item_ids": [7, 9]}
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def raise_crash(request):
    raise RuntimeError("boom at C:/secret/path.py")


@api_view(["GET"])
def private(request):
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([IsAdminRole])
def admin_only(request):
    return Response({"ok": True})


urlpatterns = real_urlpatterns + [
    path("api/_test/validation/", raise_validation),
    path("api/_test/domain/", raise_domain),
    path("api/_test/crash/", raise_crash),
    path("api/_test/private/", private),
    path("api/_test/admin/", admin_only),
]

handler404 = "common.views.json_404"
handler500 = "common.views.json_500"
