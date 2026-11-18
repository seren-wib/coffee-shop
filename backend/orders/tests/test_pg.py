"""TossPaymentsClient without the network: urlopen is replaced (STP 1.2)."""

import base64
import io
import json
import socket
import urllib.error
from unittest import mock

from django.test import SimpleTestCase, override_settings

from orders.pg import PgError, TossPaymentsClient


class _Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@override_settings(TOSS_SECRET_KEY="test_sk_fake")
class TossClientTests(SimpleTestCase):
    def test_fr26_confirm_sends_basic_auth_and_parses_result(self):
        body = {
            "status": "DONE",
            "totalAmount": 30000,
            "method": "카드",
            "approvedAt": "2026-11-20T14:04:02+09:00",
            "card": {"number": "1234****"},
        }
        with mock.patch(
            "orders.pg.urllib.request.urlopen",
            return_value=_Response(json.dumps(body).encode()),
        ) as urlopen:
            result = TossPaymentsClient().confirm(
                "tkey_1", "ORD-20261120-001-P1", 30000
            )
        request = urlopen.call_args.args[0]
        expected = base64.b64encode(b"test_sk_fake:").decode()
        self.assertEqual(request.get_header("Authorization"), f"Basic {expected}")
        self.assertEqual(
            json.loads(urlopen.call_args.kwargs["data"]),
            {"paymentKey": "tkey_1", "orderId": "ORD-20261120-001-P1", "amount": 30000},
        )
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 10)
        self.assertTrue(result.ok)
        self.assertEqual(result.total_amount, 30000)
        self.assertEqual(result.approved_at.utcoffset().total_seconds(), 9 * 3600)
        # Card details in the response are not kept (NFR-18).
        self.assertFalse(hasattr(result, "card"))

    def test_fr28_http_error_returns_code_and_message(self):
        error = urllib.error.HTTPError(
            "url",
            400,
            "Bad Request",
            {},
            io.BytesIO(
                json.dumps({"code": "REJECT_CARD_COMPANY", "message": "한도"}).encode()
            ),
        )
        with mock.patch("orders.pg.urllib.request.urlopen", side_effect=error):
            result = TossPaymentsClient().confirm("tkey_1", "ORD-20261120-001-P1", 1)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "REJECT_CARD_COMPANY")

    def test_fr26_timeout_raises_pg_error(self):
        for exc in (socket.timeout(), urllib.error.URLError(TimeoutError())):
            with mock.patch("orders.pg.urllib.request.urlopen", side_effect=exc):
                with self.assertRaises(PgError) as ctx:
                    TossPaymentsClient().get("tkey_1")
            self.assertEqual(ctx.exception.code, "TIMEOUT")

    def test_fr50_cancel_sends_idempotency_key(self):
        with mock.patch(
            "orders.pg.urllib.request.urlopen", return_value=_Response(b"{}")
        ) as urlopen:
            TossPaymentsClient().cancel("tkey_1", "관리자 취소 승인", "cancel-9")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Idempotency-key"), "cancel-9")
        self.assertTrue(request.full_url.endswith("/v1/payments/tkey_1/cancel"))

    def test_fr26_unknown_outcomes_raise_pg_error(self):
        server_error = urllib.error.HTTPError(
            "url", 502, "Bad Gateway", {}, io.BytesIO(b"<html>bad gateway</html>")
        )
        cases = (
            {"side_effect": server_error},
            {"return_value": _Response(b"<html>not json</html>")},
            {"side_effect": ConnectionResetError()},
        )
        for kwargs in cases:
            with mock.patch("orders.pg.urllib.request.urlopen", **kwargs):
                with self.assertRaises(PgError):
                    TossPaymentsClient().confirm("tkey_1", "ORD-20261120-001-P1", 1)
