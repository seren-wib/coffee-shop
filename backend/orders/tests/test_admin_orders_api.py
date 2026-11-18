from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from common.tests.helpers import auth_client
from orders.models import Order, OrderStatus, Payment, PaymentStatus
from orders.pg import FakePaymentsClient, PgResult
from orders.tests.factories import make_order, make_payment
from products.models import ProductOption
from products.tests.factories import make_product
from users.models import Role
from users.tests.factories import make_member

ADMIN = "/api/admin/orders/"


class AdminOrderApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        FakePaymentsClient.reset()
        self.admin = make_member(role=Role.ADMIN)
        self.client = auth_client(self.admin)
        self.member = make_member(email="kim@example.com")
        self.option = make_product(options=[{"stock_quantity": 5}]).options.get()

    def _order(self, status=OrderStatus.PAID, user=None, **fields):
        return make_order(
            user or self.member, self.option, quantity=2, status=status, **fields
        )

    def _post(self, order, action, body=None):
        return self.client.post(
            f"{ADMIN}{order.order_id}/{action}/", body or {}, format="json"
        )

    def _status(self, order):
        return Order.objects.get(pk=order.pk).order_status

    def test_fr44_list_all_orders_newest_first(self):
        old = self._order()
        Order.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )
        other = self._order(user=make_member())
        res = self.client.get(ADMIN)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["count"], 2)
        self.assertEqual(
            [o["order_id"] for o in body["results"]], [other.order_id, old.order_id]
        )
        self.assertEqual(
            set(body["results"][0]),
            {
                "order_id",
                "created_at",
                "member_email",
                "member_name",
                "final_payment_amt",
                "status",
            },
        )

    def test_fr45_filter_by_status(self):
        self._order()
        wanted = self._order(
            status=OrderStatus.CANCEL_REQUESTED, status_before_cancel=OrderStatus.PAID
        )
        res = self.client.get(ADMIN, {"status": "CANCEL_REQUESTED"})
        self.assertEqual(
            [o["order_id"] for o in res.json()["results"]], [wanted.order_id]
        )
        self.assertEqual(self.client.get(ADMIN, {"status": "LOST"}).status_code, 400)

    def test_fr57_search_by_number_or_email(self):
        mine = self._order(order_id="ORD-20261011-001")
        other = self._order(
            user=make_member(email="lee@example.com"), order_id="ORD-20261012-001"
        )
        by_number = self.client.get(ADMIN, {"search": "20261011"}).json()["results"]
        by_email = self.client.get(ADMIN, {"search": "lee@"}).json()["results"]
        self.assertEqual([o["order_id"] for o in by_number], [mine.order_id])
        self.assertEqual([o["order_id"] for o in by_email], [other.order_id])
        both = self.client.get(ADMIN, {"search": "ORD-2026101", "status": "PENDING"})
        self.assertEqual(both.json()["count"], 0)

    def test_fr46_order_detail(self):
        order = self._order(
            status=OrderStatus.CANCEL_REQUESTED,
            status_before_cancel=OrderStatus.PREPARING,
            cancel_reason="단순 변심",
        )
        make_payment(order, 1, PaymentStatus.SUCCESS, pg_tid="tkey_1234567890abcdef")
        res = self.client.get(f"{ADMIN}{order.order_id}/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["member"]["email"], "kim@example.com")
        self.assertEqual(body["status_before_cancel"], OrderStatus.PREPARING)
        self.assertEqual(body["cancel_reason"], "단순 변심")
        self.assertEqual(body["payments"][0]["pg_order_id"], f"{order.order_id}-P1")
        self.assertEqual(body["payments"][0]["pg_tid"], "90abcdef")
        self.assertEqual(body["allowed_actions"], ["cancel_approve", "cancel_reject"])
        self.assertEqual(len(body["items"]), 1)

    def test_fr47_prepare(self):
        order = self._order()
        res = self._post(order, "prepare")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], OrderStatus.PREPARING)
        self.assertEqual(res.json()["allowed_actions"], ["ship"])
        pending = self._order(status=OrderStatus.PENDING)
        res = self._post(pending, "prepare")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "INVALID_STATE")

    def test_fr48_ship(self):
        order = self._order(status=OrderStatus.PREPARING)
        self.assertEqual(
            self._post(
                order, "ship", {"courier_code": "CJ", "tracking_number": ""}
            ).status_code,
            400,
        )
        self.assertEqual(
            self._post(
                order, "ship", {"courier_code": "DHL", "tracking_number": "123"}
            ).status_code,
            400,
        )
        self.assertEqual(
            self._post(
                order, "ship", {"courier_code": "CJ", "tracking_number": "12a"}
            ).status_code,
            400,
        )
        res = self._post(
            order, "ship", {"courier_code": "CJ", "tracking_number": "1234-5678"}
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["status"], OrderStatus.SHIPPED)
        self.assertEqual(body["courier_name"], "CJ대한통운")
        self.assertIsNotNone(body["shipped_at"])
        stored = Order.objects.get(pk=order.pk)
        self.assertEqual(stored.courier_code, "CJ")
        again = self._post(
            order, "ship", {"courier_code": "CJ", "tracking_number": "1"}
        )
        self.assertEqual(again.status_code, 409)

    def test_fr49_deliver(self):
        order = self._order(
            status=OrderStatus.SHIPPED,
            courier_code="CJ",
            tracking_number="1",
            shipped_at=timezone.now(),
        )
        res = self._post(order, "deliver")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], OrderStatus.DELIVERED)
        self.assertIsNotNone(res.json()["delivered_at"])
        self.assertEqual(self._post(order, "deliver").status_code, 409)

    def test_fr50_approve_cancel(self):
        order = self._order(
            status=OrderStatus.CANCEL_REQUESTED, status_before_cancel=OrderStatus.PAID
        )
        payment = make_payment(order, 1, PaymentStatus.SUCCESS, pg_tid="tkey_done")
        res = self._post(order, "cancel-approve")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], OrderStatus.CANCELLED)
        self.assertEqual(ProductOption.objects.get(pk=self.option.pk).stock_quantity, 7)
        self.assertEqual(
            Payment.objects.get(pk=payment.pk).payment_status, PaymentStatus.CANCELLED
        )
        self.assertEqual(len(FakePaymentsClient.calls_to("cancel")), 1)
        again = self._post(order, "cancel-approve")
        self.assertEqual(again.status_code, 409)
        self.assertEqual(ProductOption.objects.get(pk=self.option.pk).stock_quantity, 7)

    def test_fr50_pg_error_keeps_cancel_requested(self):
        order = self._order(
            status=OrderStatus.CANCEL_REQUESTED, status_before_cancel=OrderStatus.PAID
        )
        make_payment(order, 1, PaymentStatus.SUCCESS, pg_tid="tkey_done")
        FakePaymentsClient.script["cancel"] = [
            PgResult(ok=False, code="PROVIDER_ERROR", message="잠시 후")
        ]
        res = self._post(order, "cancel-approve")
        self.assertEqual(res.status_code, 502)
        self.assertEqual(res.json()["code"], "PG_ERROR")
        self.assertEqual(self._status(order), OrderStatus.CANCEL_REQUESTED)
        self.assertEqual(ProductOption.objects.get(pk=self.option.pk).stock_quantity, 5)

    def test_fr51_reject_cancel_restores_previous_status(self):
        for before in (OrderStatus.PAID, OrderStatus.PREPARING):
            order = self._order(
                status=OrderStatus.CANCEL_REQUESTED,
                status_before_cancel=before,
                cancel_reason="변심",
            )
            res = self._post(order, "cancel-reject")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["status"], before)
            stored = Order.objects.get(pk=order.pk)
            self.assertIsNone(stored.status_before_cancel)
            self.assertEqual(stored.cancel_reason, "변심")

    def test_nfr11_admin_routes_take_any_members_order(self):
        order = self._order(user=make_member())
        self.assertEqual(self.client.get(f"{ADMIN}{order.order_id}/").status_code, 200)
        self.assertEqual(self.client.get(f"{ADMIN}ORD-20000101-001/").status_code, 404)
