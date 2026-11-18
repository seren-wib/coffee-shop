from django.test import TestCase

from common.exceptions import DomainError
from products import services
from products.models import GrindType, Product, ProductOption, SalesStatus, WeightSize
from products.tests.factories import make_product


def _status(product):
    return Product.objects.values_list("sales_status", flat=True).get(pk=product.pk)


def _stock(option):
    return ProductOption.objects.values_list("stock_quantity", flat=True).get(
        pk=option.pk
    )


TWO_OPTIONS = [
    {"weight_size": WeightSize.G200, "grind_type": GrindType.WHOLE_BEAN},
    {"weight_size": WeightSize.G500, "grind_type": GrindType.WHOLE_BEAN},
]


class DecreaseStockTests(TestCase):
    def test_dr5_decrease_stock_rejects_more_than_left(self):
        option = make_product(options=[{"stock_quantity": 2}]).options.get()
        with self.assertRaises(DomainError) as ctx:
            services.decrease_stock(option.pk, 3)
        self.assertEqual(ctx.exception.code, "OUT_OF_STOCK")
        self.assertEqual(ctx.exception.status, 409)
        self.assertEqual(_stock(option), 2)

    def test_dr5_decrease_stock_subtracts_in_db(self):
        option = make_product(options=[{"stock_quantity": 5}]).options.get()
        services.decrease_stock(option.pk, 2)
        self.assertEqual(_stock(option), 3)

    def test_dr10_decrease_stock_rejects_non_positive_quantity(self):
        option = make_product(options=[{"stock_quantity": 5}]).options.get()
        with self.assertRaises(DomainError) as ctx:
            services.decrease_stock(option.pk, 0)
        self.assertEqual(ctx.exception.status, 400)
        self.assertEqual(_stock(option), 5)

    def test_dr6_last_stock_sold_marks_product_sold_out(self):
        product = make_product(options=[{"stock_quantity": 1}])
        services.decrease_stock(product.options.get().pk, 1)
        self.assertEqual(_status(product), SalesStatus.SOLD_OUT)

    def test_dr6_sold_out_only_when_all_options_empty(self):
        product = make_product(
            options=[
                {**TWO_OPTIONS[0], "stock_quantity": 1},
                {**TWO_OPTIONS[1], "stock_quantity": 4},
            ]
        )
        option = product.options.get(weight_size=WeightSize.G200)
        services.decrease_stock(option.pk, 1)
        self.assertEqual(_status(product), SalesStatus.ON_SALE)


class IncreaseStockTests(TestCase):
    def test_dr6_increase_stock_returns_sold_out_to_on_sale(self):
        product = make_product(
            options=[{"stock_quantity": 0}], sales_status=SalesStatus.SOLD_OUT
        )
        option = product.options.get()
        services.increase_stock(option.pk, 2)
        self.assertEqual(_stock(option), 2)
        self.assertEqual(_status(product), SalesStatus.ON_SALE)

    def test_dr10_increase_stock_rejects_non_positive_quantity(self):
        option = make_product(options=[{"stock_quantity": 5}]).options.get()
        with self.assertRaises(DomainError) as ctx:
            services.increase_stock(option.pk, -1)
        self.assertEqual(ctx.exception.status, 400)
        self.assertEqual(_stock(option), 5)


class SetStockTests(TestCase):
    def test_dr5_set_stock_rejects_negative(self):
        option = make_product(options=[{"stock_quantity": 4}]).options.get()
        with self.assertRaises(DomainError) as ctx:
            services.set_stock(option.pk, -1)
        self.assertEqual(ctx.exception.code, "VALIDATION_ERROR")
        self.assertEqual(ctx.exception.status, 400)
        self.assertEqual(_stock(option), 4)

    def test_dr6_restock_returns_sold_out_to_on_sale(self):
        product = make_product(
            options=[{"stock_quantity": 0}], sales_status=SalesStatus.SOLD_OUT
        )
        option = product.options.get()
        services.set_stock(option.pk, 3)
        self.assertEqual(_stock(option), 3)
        self.assertEqual(_status(product), SalesStatus.ON_SALE)

    def test_fr41_set_stock_zero_on_every_option_marks_sold_out(self):
        product = make_product(
            options=[
                {**TWO_OPTIONS[0], "stock_quantity": 0},
                {**TWO_OPTIONS[1], "stock_quantity": 3},
            ]
        )
        option = product.options.get(weight_size=WeightSize.G500)
        services.set_stock(option.pk, 0)
        self.assertEqual(_status(product), SalesStatus.SOLD_OUT)

    def test_fr41_set_stock_unknown_option_is_404(self):
        with self.assertRaises(DomainError) as ctx:
            services.set_stock(999999, 1)
        self.assertEqual(ctx.exception.status, 404)


class StoppedProductTests(TestCase):
    def test_dr7_stopped_product_stays_stopped_on_stock_change(self):
        product = make_product(
            options=[{"stock_quantity": 1}], sales_status=SalesStatus.STOPPED
        )
        option = product.options.get()
        services.decrease_stock(option.pk, 1)
        self.assertEqual(_status(product), SalesStatus.STOPPED)
        services.increase_stock(option.pk, 2)
        self.assertEqual(_status(product), SalesStatus.STOPPED)
        services.set_stock(option.pk, 0)
        self.assertEqual(_status(product), SalesStatus.STOPPED)
        services.set_stock(option.pk, 5)
        self.assertEqual(_status(product), SalesStatus.STOPPED)


class SalesStatusTests(TestCase):
    def test_fr42_stop_sales_from_on_sale_and_sold_out(self):
        for status in (SalesStatus.ON_SALE, SalesStatus.SOLD_OUT):
            product = make_product(sales_status=status)
            services.stop_sales(product.pk)
            self.assertEqual(_status(product), SalesStatus.STOPPED)

    def test_fr42_stop_sales_twice_is_409(self):
        product = make_product(sales_status=SalesStatus.STOPPED)
        with self.assertRaises(DomainError) as ctx:
            services.stop_sales(product.pk)
        self.assertEqual(ctx.exception.code, "INVALID_STATE")
        self.assertEqual(ctx.exception.status, 409)

    def test_fr42_stop_sales_unknown_product_is_404(self):
        with self.assertRaises(DomainError) as ctx:
            services.stop_sales(999999)
        self.assertEqual(ctx.exception.status, 404)

    def test_fr43_resume_picks_status_from_stock(self):
        in_stock = make_product(
            options=[{"stock_quantity": 2}], sales_status=SalesStatus.STOPPED
        )
        empty = make_product(
            options=[{"stock_quantity": 0}], sales_status=SalesStatus.STOPPED
        )
        services.resume_sales(in_stock.pk)
        services.resume_sales(empty.pk)
        self.assertEqual(_status(in_stock), SalesStatus.ON_SALE)
        self.assertEqual(_status(empty), SalesStatus.SOLD_OUT)

    def test_fr43_resume_without_options_is_on_sale(self):
        product = make_product(options=[], sales_status=SalesStatus.STOPPED)
        services.resume_sales(product.pk)
        self.assertEqual(_status(product), SalesStatus.ON_SALE)

    def test_fr43_resume_when_not_stopped_is_409(self):
        product = make_product()
        with self.assertRaises(DomainError) as ctx:
            services.resume_sales(product.pk)
        self.assertEqual(ctx.exception.code, "INVALID_STATE")
        self.assertEqual(_status(product), SalesStatus.ON_SALE)


class CustomerQueryTests(TestCase):
    def test_fr1_customer_products_hide_stopped(self):
        from products import queries

        on_sale = make_product()
        sold_out = make_product(sales_status=SalesStatus.SOLD_OUT)
        stopped = make_product(sales_status=SalesStatus.STOPPED)
        ids = set(queries.customer_products().values_list("pk", flat=True))
        self.assertIn(on_sale.pk, ids)
        self.assertIn(sold_out.pk, ids)
        self.assertNotIn(stopped.pk, ids)
