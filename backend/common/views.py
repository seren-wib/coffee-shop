"""Health check and JSON error pages for requests DRF does not handle (SDD 4.9.1, 7.2)."""

import logging

from django.db import connection
from django.http import JsonResponse
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        logger.exception("health check failed")
        return Response({"status": "unavailable"}, status=503)
    return Response({"status": "ok"})


def json_404(request, exception=None):
    return JsonResponse(
        {"code": "NOT_FOUND", "message": "찾을 수 없습니다."},
        status=404,
        json_dumps_params={"ensure_ascii": False},
    )


def json_500(request):
    return JsonResponse(
        {"code": "SERVER_ERROR", "message": "일시적인 오류가 발생했습니다."},
        status=500,
        json_dumps_params={"ensure_ascii": False},
    )
