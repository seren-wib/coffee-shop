from datetime import datetime, timedelta, timezone as dt_timezone
from unittest import mock

import jwt
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from users.models import Role, User
from users.tests.factories import make_member
from users.tests.helpers import auth_client

REGISTER = "/api/auth/register/"
TOKEN = "/api/auth/token/"
REFRESH = "/api/auth/token/refresh/"
ME = "/api/me/"
PASSWORD = "/api/me/password/"

PUBLIC = {
    "api/health/",
    "api/auth/register/",
    "api/auth/token/",
    "api/auth/token/refresh/",
    "api/products/",
    "api/products/<int:pk>/",
}


def _signup(**overrides):
    data = {
        "email": "new@example.com",
        "password": "pass1234",
        "user_name": "새회원",
        "phone_number": "010-1234-5678",
        "privacy_agreed": True,
    }
    data.update(overrides)
    return {k: v for k, v in data.items() if v is not None}


def _api_routes(resolver=None, prefix=""):
    resolver = resolver or get_resolver()
    for p in resolver.url_patterns:
        route = prefix + str(p.pattern)
        if isinstance(p, URLResolver):
            yield from _api_routes(p, route)
        elif isinstance(p, URLPattern) and route.startswith("api/"):
            yield route


def _sample_path(route):
    path = route.replace("<int:pk>", "1").replace("<str:pk>", "ORD-20261130-001")
    for token in ("<int:", "<str:"):
        while token in path:
            start = path.index(token)
            path = path[:start] + "1" + path[path.index(">", start) + 1 :]
    return "/" + path


class RegisterTests(APITestCase):
    def test_fr7_register_creates_member(self):
        res = self.client.post(REGISTER, _signup(), format="json")
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(body["role"], Role.MEMBER)
        self.assertEqual(body["email"], "new@example.com")
        self.assertNotIn("password", body)
        self.assertEqual(
            set(body), {"user_id", "email", "user_name", "phone_number", "role"}
        )

    def test_fr7_register_ignores_role_admin(self):
        res = self.client.post(REGISTER, _signup(role="ADMIN"), format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(User.objects.get().role, Role.MEMBER)

    def test_fr7_register_rejects_duplicate_email(self):
        make_member(email="new@example.com")
        res = self.client.post(
            REGISTER, _signup(email="NEW@Example.com"), format="json"
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.json()["fields"])

    def test_fr7_register_rejects_short_password(self):
        res = self.client.post(REGISTER, _signup(password="pass123"), format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("password", res.json()["fields"])

    def test_fr58_register_requires_privacy_agreement(self):
        for agreed in (None, False):
            res = self.client.post(
                REGISTER, _signup(privacy_agreed=agreed), format="json"
            )
            self.assertEqual(res.status_code, 400)
            self.assertIn("privacy_agreed", res.json()["fields"])
        self.assertEqual(User.objects.count(), 0)

    def test_fr58_register_stores_agreement_time(self):
        fixed = datetime(2026, 11, 20, 1, 2, 3, tzinfo=dt_timezone.utc)
        with mock.patch("django.utils.timezone.now", return_value=fixed):
            res = self.client.post(REGISTER, _signup(), format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(User.objects.get().privacy_agreed_at, fixed)

    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.PBKDF2PasswordHasher"]
    )
    def test_nfr6_password_stored_as_pbkdf2_hash(self):
        self.client.post(REGISTER, _signup(), format="json")
        stored = User.objects.get().password
        self.assertTrue(stored.startswith("pbkdf2_sha256$"))
        self.assertNotIn("pass1234", stored)


class TokenTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_member(email="kim@example.com", password="pass1234")

    def test_fr8_login_returns_tokens(self):
        res = self.client.post(
            TOKEN, {"email": "kim@example.com", "password": "pass1234"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("access", body)
        self.assertIn("refresh", body)
        self.assertEqual(
            body["user"],
            {
                "user_id": self.user.user_id,
                "email": "kim@example.com",
                "user_name": self.user.user_name,
                "role": Role.MEMBER,
            },
        )

    def test_fr8_nfr7_unknown_email_and_wrong_password_look_same(self):
        unknown = self.client.post(
            TOKEN,
            {"email": "nobody@example.com", "password": "pass1234"},
            format="json",
        )
        wrong = self.client.post(
            TOKEN, {"email": "kim@example.com", "password": "wrong999"}, format="json"
        )
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(unknown.content, wrong.content)
        self.assertEqual(unknown.json()["code"], "INVALID_CREDENTIALS")

    def test_fr8_inactive_account_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        res = self.client.post(
            TOKEN, {"email": "kim@example.com", "password": "pass1234"}, format="json"
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["code"], "INVALID_CREDENTIALS")

    def test_nfr8_token_lifetimes(self):
        body = self.client.post(
            TOKEN, {"email": "kim@example.com", "password": "pass1234"}, format="json"
        ).json()
        access = jwt.decode(body["access"], options={"verify_signature": False})
        refresh = jwt.decode(body["refresh"], options={"verify_signature": False})
        self.assertEqual(access["exp"] - access["iat"], 1800)
        self.assertEqual(refresh["exp"] - refresh["iat"], 604800)
        self.assertEqual(access["role"], Role.MEMBER)
        self.assertNotIn("email", access)

    def test_fr9_refresh_issues_access(self):
        refresh = self.client.post(
            TOKEN, {"email": "kim@example.com", "password": "pass1234"}, format="json"
        ).json()["refresh"]
        res = self.client.post(REFRESH, {"refresh": refresh}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.json())

    def test_fr9_expired_or_forged_refresh_is_401(self):
        now = datetime.now(dt_timezone.utc)
        claims = {
            "token_type": "refresh",
            "user_id": self.user.user_id,
            "jti": "x",
            "iat": int((now - timedelta(days=8)).timestamp()),
            "exp": int((now - timedelta(days=1)).timestamp()),
        }
        expired = jwt.encode(claims, settings.SECRET_KEY, algorithm="HS256")
        claims["exp"] = int((now + timedelta(days=1)).timestamp())
        forged = jwt.encode(claims, "not-the-key", algorithm="HS256")
        for token in (expired, forged, "garbage"):
            res = self.client.post(REFRESH, {"refresh": token}, format="json")
            self.assertEqual(res.status_code, 401)
            self.assertEqual(res.json()["code"], "INVALID_TOKEN")

    def test_login_throttle_returns_429(self):
        with mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"login": "10/min"}):
            codes = [
                self.client.post(
                    TOKEN,
                    {"email": "kim@example.com", "password": "wrong999"},
                    format="json",
                ).status_code
                for _ in range(11)
            ]
            res = self.client.post(
                TOKEN,
                {"email": "kim@example.com", "password": "pass1234"},
                format="json",
            )
        self.assertEqual(codes[:10], [401] * 10)
        self.assertEqual(codes[10], 429)
        self.assertEqual(res.status_code, 429)
        self.assertEqual(res.json()["code"], "THROTTLED")


class MeTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_member(email="me@example.com", password="pass1234")
        make_member(email="other@example.com")
        self.client = auth_client(self.user)

    def test_fr11_me_returns_own_profile(self):
        res = self.client.get(ME)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["email"], "me@example.com")
        self.assertEqual(
            set(res.json()), {"user_id", "email", "user_name", "phone_number", "role"}
        )

    def test_fr12_me_update_keeps_email(self):
        res = self.client.patch(
            ME,
            {"user_name": "바뀐이름", "email": "hack@example.com", "role": "ADMIN"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.user_name, "바뀐이름")
        self.assertEqual(self.user.email, "me@example.com")
        self.assertEqual(self.user.role, Role.MEMBER)

    def test_fr12_me_update_rejects_bad_phone_and_empty_name(self):
        for data, field in (
            ({"phone_number": "010-12ab"}, "phone_number"),
            ({"user_name": ""}, "user_name"),
        ):
            res = self.client.patch(ME, data, format="json")
            self.assertEqual(res.status_code, 400)
            self.assertIn(field, res.json()["fields"])

    def test_fr13_password_change(self):
        res = self.client.post(
            PASSWORD,
            {"current_password": "pass1234", "new_password": "newpass99"},
            format="json",
        )
        self.assertEqual(res.status_code, 204)
        old = self.client.post(
            TOKEN, {"email": "me@example.com", "password": "pass1234"}, format="json"
        )
        new = self.client.post(
            TOKEN, {"email": "me@example.com", "password": "newpass99"}, format="json"
        )
        self.assertEqual(old.status_code, 401)
        self.assertEqual(new.status_code, 200)

    def test_fr13_wrong_current_password_is_400(self):
        res = self.client.post(
            PASSWORD,
            {"current_password": "wrong999", "new_password": "newpass99"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("current_password", res.json()["fields"])

    def test_fr13_short_new_password_is_400(self):
        res = self.client.post(
            PASSWORD,
            {"current_password": "pass1234", "new_password": "short1"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("new_password", res.json()["fields"])


class RouteGuardTests(APITestCase):
    def test_nfr9_every_private_route_needs_token(self):
        private = [r for r in _api_routes() if r not in PUBLIC]
        self.assertIn("api/me/", private)
        for route in private:
            path = _sample_path(route)
            for method in ("get", "post", "patch", "delete"):
                res = getattr(self.client, method)(path, {}, format="json")
                if res.status_code == 405:
                    continue
                self.assertEqual(res.status_code, 401, f"{method.upper()} {path}")

    def test_nfr10_member_token_on_admin_routes_is_403(self):
        client = auth_client(make_member())
        for route in _api_routes():
            if not route.startswith("api/admin/"):
                continue
            path = _sample_path(route)
            for method in ("get", "post", "patch", "delete"):
                res = getattr(client, method)(path, {}, format="json")
                if res.status_code == 405:
                    continue
                self.assertEqual(res.status_code, 403, f"{method.upper()} {path}")
