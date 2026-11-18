from unittest import mock

from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from users.models import Role
from users.tests.factories import make_member

TEST_URLS = "common.tests.urls"


class HealthTests(APITestCase):
    def test_fr52_health_ok(self):
        res = self.client.get("/api/health/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

    def test_fr52_health_503_when_db_fails(self):
        with mock.patch("common.views.connection") as conn:
            conn.cursor.side_effect = RuntimeError("disk I/O error at /srv/data")
            res = self.client.get("/api/health/")
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.json(), {"status": "unavailable"})


@override_settings(ROOT_URLCONF=TEST_URLS)
class ErrorShapeTests(APITestCase):
    def test_nfr30_validation_error_lists_fields(self):
        res = self.client.post(
            "/api/_test/validation/", {"name": "toolong"}, format="json"
        )
        self.assertEqual(res.status_code, 400)
        body = res.json()
        self.assertEqual(body["code"], "VALIDATION_ERROR")
        self.assertTrue(body["message"])
        self.assertIn("name", body["fields"])
        self.assertIsInstance(body["fields"]["name"], list)

    def test_nfr30_domain_error_keeps_code_status_and_details(self):
        res = self.client.get("/api/_test/domain/")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(
            res.json(),
            {
                "code": "OUT_OF_STOCK",
                "message": "재고가 부족합니다.",
                "details": {"cart_item_ids": [7, 9]},
            },
        )

    def test_nfr9_private_view_without_token_is_401(self):
        res = self.client.get("/api/_test/private/")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["code"], "NOT_AUTHENTICATED")

    def test_nfr10_member_on_admin_view_is_403(self):
        self.client.force_authenticate(make_member())
        res = self.client.get("/api/_test/admin/")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["code"], "PERMISSION_DENIED")

    def test_nfr10_admin_on_admin_view_is_200(self):
        self.client.force_authenticate(make_member(role=Role.ADMIN))
        res = self.client.get("/api/_test/admin/")
        self.assertEqual(res.status_code, 200)

    @override_settings(DEBUG=False)
    def test_nfr12_error_bodies_have_no_trace(self):
        client = APIClient(raise_request_exception=False)
        missing = client.get("/api/no-such-route/")
        crash = client.get("/api/_test/crash/")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["code"], "NOT_FOUND")
        self.assertEqual(crash.status_code, 500)
        self.assertEqual(crash.json()["code"], "SERVER_ERROR")
        for res in (missing, crash):
            text = res.content.decode()
            self.assertNotIn("Traceback", text)
            self.assertNotIn("secret/path", text)

    def test_nfr28_responses_are_json(self):
        client = APIClient(raise_request_exception=False)
        for res in (
            client.get("/api/health/"),
            client.get("/api/_test/domain/"),
            client.get("/api/no-such-route/"),
            client.get("/api/_test/private/"),
        ):
            self.assertEqual(res["Content-Type"], "application/json")


class PaginationTests(APITestCase):
    def test_fr1_page_size_is_20_and_links_have_no_host(self):
        from django.test import RequestFactory
        from rest_framework.request import Request

        from common.pagination import StandardPagination

        paginator = StandardPagination()
        request = Request(RequestFactory().get("/api/products/?page=2&page_size=50"))
        page = paginator.paginate_queryset(list(range(45)), request)
        self.assertEqual(len(page), 20)
        data = paginator.get_paginated_response(page).data
        self.assertEqual(data["count"], 45)
        self.assertEqual(data["next"], "/api/products/?page=3&page_size=50")
        self.assertEqual(data["previous"], "/api/products/?page_size=50")
