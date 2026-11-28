"""Toss Payments calls (SDD 4.6.5). The only place that talks to the PG (SDD 2.1).

Tests use FakePaymentsClient (settings PAYMENTS_CLIENT) and never call Toss (STP 1.2).
Only the fields in PgResult are kept; the raw response is never stored (NFR-18).
"""

import base64
import http.client
import json
import logging
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime

from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework import status

from common.exceptions import DomainError

logger = logging.getLogger(__name__)


@dataclass
class PgResult:
    ok: bool
    status: str | None = None
    total_amount: int | None = None
    method: str | None = None
    approved_at: datetime | None = None
    code: str | None = None
    message: str | None = None
    order_id: str | None = None

    @property
    def approved(self):
        # Only DONE means the money was taken (e.g. a virtual account waits).
        return self.ok and self.status == "DONE"


def _json(raw):
    try:
        return json.loads(raw or b"{}")
    except ValueError as e:
        raise PgError("BAD_RESPONSE", "결제사 응답을 읽지 못했습니다.") from e


class PgError(Exception):
    """The PG could not be reached or did not answer in time (status unknown)."""

    def __init__(self, code, message=""):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def ensure_payments_enabled():
    # Off on a server without TOSS_SECRET_KEY (SIP 3): nothing reaches the PG.
    if not settings.PAYMENTS_ENABLED:
        raise DomainError(
            "PAYMENTS_DISABLED",
            "지금은 결제를 쓸 수 없습니다.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )


def get_client():
    ensure_payments_enabled()
    return import_string(settings.PAYMENTS_CLIENT)()


def masked(payment_key):
    # Logs keep only the last 8 characters of a paymentKey (SDD 9.5).
    return f"...{payment_key[-8:]}" if payment_key else payment_key


class TossPaymentsClient:
    BASE = "https://api.tosspayments.com"
    TIMEOUT = 10

    def confirm(self, payment_key, pg_order_id, amount):
        return self._call(
            "POST",
            "/v1/payments/confirm",
            {"paymentKey": payment_key, "orderId": pg_order_id, "amount": amount},
        )

    def cancel(self, payment_key, reason, idempotency_key=None):
        return self._call(
            "POST",
            f"/v1/payments/{payment_key}/cancel",
            {"cancelReason": reason},
            idempotency_key=idempotency_key,
        )

    def get(self, payment_key):
        return self._call("GET", f"/v1/payments/{payment_key}")

    def _call(self, method, path, body=None, idempotency_key=None):
        auth = base64.b64encode(f"{settings.TOSS_SECRET_KEY}:".encode()).decode()
        request = urllib.request.Request(self.BASE + path, method=method)
        request.add_header("Authorization", f"Basic {auth}")
        request.add_header("Content-Type", "application/json")
        if idempotency_key:
            request.add_header("Idempotency-Key", idempotency_key)
        data = json.dumps(body).encode() if body is not None else None
        try:
            with urllib.request.urlopen(request, data=data, timeout=self.TIMEOUT) as r:
                return self._result(_json(r.read()))
        except urllib.error.HTTPError as e:
            if e.code >= 500:
                # The PG failed on its side: whether it approved is unknown.
                raise PgError("PG_UNAVAILABLE", "결제사 응답에 문제가 있습니다.") from e
            try:
                payload = _json(e.read())
            except PgError:
                payload = {}
            logger.warning(
                "toss %s %s -> %s %s",
                method,
                path.split("/")[2],
                e.code,
                payload.get("code"),
            )
            return PgResult(
                ok=False,
                code=payload.get("code") or f"HTTP_{e.code}",
                message=payload.get("message"),
            )
        except (TimeoutError, socket.timeout) as e:
            raise PgError("TIMEOUT", "결제사 응답이 늦어지고 있습니다.") from e
        except urllib.error.URLError as e:
            if isinstance(e.reason, (TimeoutError, socket.timeout)):
                raise PgError("TIMEOUT", "결제사 응답이 늦어지고 있습니다.") from e
            raise PgError("NETWORK", "결제사에 연결하지 못했습니다.") from e
        except (OSError, http.client.HTTPException) as e:
            # Connection reset or dropped mid-response: status unknown.
            raise PgError("NETWORK", "결제사에 연결하지 못했습니다.") from e

    @staticmethod
    def _result(payload):
        approved = payload.get("approvedAt")
        return PgResult(
            ok=True,
            status=payload.get("status"),
            order_id=payload.get("orderId"),
            total_amount=payload.get("totalAmount"),
            method=payload.get("method"),
            approved_at=datetime.fromisoformat(approved) if approved else None,
        )


class FakePaymentsClient:
    """Test double. Tests put results (PgResult or PgError) in `script[<method>]`;
    with nothing scripted, confirm approves the requested amount and the rest succeed.
    Every call is recorded in `calls`."""

    script: dict = {}
    calls: list = []

    @classmethod
    def reset(cls):
        cls.script = {}
        cls.calls = []

    @classmethod
    def calls_to(cls, method):
        return [c for c in cls.calls if c["method"] == method]

    def _next(self, method, default):
        queue = type(self).script.get(method) or []
        result = queue.pop(0) if queue else default
        if isinstance(result, Exception):
            raise result
        return result

    def confirm(self, payment_key, pg_order_id, amount):
        type(self).calls.append(
            {
                "method": "confirm",
                "payment_key": payment_key,
                "pg_order_id": pg_order_id,
                "amount": amount,
            }
        )
        return self._next(
            "confirm",
            PgResult(ok=True, status="DONE", total_amount=amount, method="카드"),
        )

    def cancel(self, payment_key, reason, idempotency_key=None):
        type(self).calls.append(
            {
                "method": "cancel",
                "payment_key": payment_key,
                "reason": reason,
                "idempotency_key": idempotency_key,
            }
        )
        return self._next("cancel", PgResult(ok=True, status="CANCELED"))

    def get(self, payment_key):
        type(self).calls.append({"method": "get", "payment_key": payment_key})
        return self._next("get", PgResult(ok=True, status="DONE"))
