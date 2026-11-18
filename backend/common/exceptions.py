"""Business errors and the API error shape (SDD 4.0, 7.2)."""

from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response


class DomainError(Exception):
    """A business rule failure. The handler turns it into the 7.2 error body."""

    def __init__(self, code, message, status=status.HTTP_409_CONFLICT, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details


VALIDATION_MESSAGE = "입력값을 확인해 주세요."

# DRF exception class -> (code, Korean message). First match wins.
_DRF_ERRORS = [
    (exceptions.NotAuthenticated, "NOT_AUTHENTICATED", "로그인이 필요합니다."),
    (exceptions.AuthenticationFailed, "NOT_AUTHENTICATED", "로그인이 필요합니다."),
    (exceptions.PermissionDenied, "PERMISSION_DENIED", "권한이 없습니다."),
    (exceptions.NotFound, "NOT_FOUND", "찾을 수 없습니다."),
    (
        exceptions.Throttled,
        "THROTTLED",
        "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
    ),
    (
        exceptions.MethodNotAllowed,
        "METHOD_NOT_ALLOWED",
        "허용되지 않는 요청 방식입니다.",
    ),
    (exceptions.ParseError, "VALIDATION_ERROR", VALIDATION_MESSAGE),
]


def error_body(code, message, fields=None, details=None):
    body = {"code": code, "message": message}
    if fields is not None:
        body["fields"] = fields
    if details:
        body["details"] = details
    return body


def _messages(value):
    if isinstance(value, dict):
        return {k: _messages(v) for k, v in value.items()}
    if isinstance(value, list):
        if value and all(isinstance(v, dict) for v in value):
            return [_messages(v) for v in value]
        return [str(v) for v in value]
    return [str(value)]


def _fields(detail):
    if isinstance(detail, dict):
        return _messages(detail)
    return {"non_field_errors": _messages(detail)}


def api_exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return Response(
            error_body(exc.code, exc.message, details=exc.details), status=exc.status
        )
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    if isinstance(exc, exceptions.ValidationError):
        return Response(
            error_body(
                "VALIDATION_ERROR", VALIDATION_MESSAGE, fields=_fields(exc.detail)
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(exc, exceptions.APIException):
        code, message = "ERROR", str(exc.detail)
        for cls, c, m in _DRF_ERRORS:
            if isinstance(exc, cls):
                code, message = c, m
                break
        response = Response(error_body(code, message), status=exc.status_code)
        if getattr(exc, "auth_header", None):
            response["WWW-Authenticate"] = exc.auth_header
        if getattr(exc, "wait", None) is not None:
            response["Retry-After"] = str(int(exc.wait))
        return response
    # Anything else propagates to Django and ends in common.views.json_500.
    return None
