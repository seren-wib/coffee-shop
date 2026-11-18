import time

from django.db import OperationalError
from django.http import HttpResponseNotAllowed, JsonResponse

from .services import DomainError, create_order


def health(request):
    return JsonResponse({"ok": True})


def orders(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    user_id = int(request.headers["X-User-Id"])
    started = time.perf_counter()
    try:
        order = create_order(user_id)
    except DomainError as e:
        body, status = {"code": e.code}, e.status
    except OperationalError as e:
        # "database is locked" lands here; the load script counts it.
        body, status = {"code": "DB_ERROR", "message": str(e)}, 500
    else:
        body, status = {"order_id": order.order_id}, 201
    body["server_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return JsonResponse(body, status=status)
