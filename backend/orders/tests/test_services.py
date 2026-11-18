from django.test import TestCase

from common.exceptions import DomainError
from orders import services
from orders.models import CartItem
from products.models import SalesStatus
from products.tests.factories import make_product
from users.tests.factories import make_member


class CartServiceTests(TestCase):
    def setUp(self):
        self.user = make_member()

    def test_dr9_adding_same_option_merges_quantity(self):
        option = make_product(options=[{"stock_quantity": 10}]).options.get()
        _, created = services.add_to_cart(self.user, option.option_id, 2)
        item, created_again = services.add_to_cart(self.user, option.option_id, 3)
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 1)
        self.assertEqual(item.quantity, 5)

    def test_dr8_cannot_add_unavailable_option(self):
        sold_out = make_product(
            sales_status=SalesStatus.SOLD_OUT, options=[{"stock_quantity": 0}]
        ).options.get()
        stopped = make_product(sales_status=SalesStatus.STOPPED).options.get()
        empty = make_product(
            options=[
                {"stock_quantity": 0},
                {"stock_quantity": 5, "weight_size": "500G"},
            ]
        ).options.get(stock_quantity=0)
        for option, code in (
            (sold_out, "NOT_AVAILABLE"),
            (stopped, "NOT_AVAILABLE"),
            (empty, "OUT_OF_STOCK"),
        ):
            with self.assertRaises(DomainError) as ctx:
                services.add_to_cart(self.user, option.option_id, 1)
            self.assertEqual(ctx.exception.code, code)
            self.assertEqual(ctx.exception.status, 409)
        self.assertFalse(CartItem.objects.exists())

    def test_dr10_merged_quantity_cannot_exceed_stock(self):
        option = make_product(options=[{"stock_quantity": 3}]).options.get()
        services.add_to_cart(self.user, option.option_id, 2)
        with self.assertRaises(DomainError) as ctx:
            services.add_to_cart(self.user, option.option_id, 2)
        self.assertEqual(ctx.exception.code, "OUT_OF_STOCK")
        self.assertEqual(CartItem.objects.get().quantity, 2)

    def test_dr14_shipping_fee_boundary(self):
        self.assertEqual(services.shipping_fee_for(29999), 3000)
        self.assertEqual(services.shipping_fee_for(30000), 0)
        self.assertEqual(services.shipping_fee_for(0), 0)
