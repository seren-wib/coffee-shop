from django.db import IntegrityError, transaction
from django.test import TestCase

from products.models import GrindType, ProductOption, SalesStatus, WeightSize
from products.tests.factories import make_product


class ProductModelTests(TestCase):
    def test_dr4_option_price_is_base_plus_extra(self):
        product = make_product(base_price=18000, options=[{"extra_price": 4000}])
        self.assertEqual(product.options.get().price, 22000)

    def test_dr6_new_product_is_on_sale(self):
        self.assertEqual(make_product().sales_status, SalesStatus.ON_SALE)

    def test_dr3_same_size_and_grind_is_rejected(self):
        product = make_product()
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductOption.objects.create(
                product=product,
                weight_size=WeightSize.G200,
                grind_type=GrindType.WHOLE_BEAN,
            )

    def test_dr5_stock_cannot_be_negative(self):
        option = make_product().options.get()
        option.stock_quantity = -1
        with self.assertRaises(IntegrityError), transaction.atomic():
            option.save()

    def test_dr4_extra_price_cannot_be_negative(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_product(options=[{"extra_price": -1}])

    def test_dr1_roast_level_check(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_product(roast_level="BURNT")
