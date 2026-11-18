from datetime import date, datetime, timezone as dt_timezone
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from common.exceptions import DomainError
from orders.order_number import next_order_id
from orders.tests.factories import make_order
from products.tests.factories import make_product
from users.tests.factories import make_member


class OrderNumberTests(TestCase):
    def setUp(self):
        self.user = make_member()
        self.option = make_product().options.get()

    def test_dr11_order_number_format(self):
        self.assertEqual(next_order_id(date(2026, 11, 30)), "ORD-20261130-001")

    def test_dr11_order_number_resets_daily_in_seoul_time(self):
        make_order(self.user, self.option, order_id="ORD-20261130-005")
        self.assertEqual(next_order_id(date(2026, 11, 30)), "ORD-20261130-006")
        # 2026-12-01 00:01 KST is still 2026-11-30 in UTC.
        just_after_midnight = datetime(2026, 11, 30, 15, 1, tzinfo=dt_timezone.utc)
        with mock.patch("django.utils.timezone.now", return_value=just_after_midnight):
            today = timezone.localdate()
        self.assertEqual(next_order_id(today), "ORD-20261201-001")

    def test_dr11_order_limit_after_999(self):
        make_order(self.user, self.option, order_id="ORD-20261130-999")
        with self.assertRaises(DomainError) as ctx:
            next_order_id(date(2026, 11, 30))
        self.assertEqual(ctx.exception.code, "ORDER_LIMIT")
        self.assertEqual(ctx.exception.status, 503)
