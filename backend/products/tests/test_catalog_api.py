from rest_framework.test import APITestCase

from products.models import GrindType, SalesStatus, WeightSize
from products.tests.factories import make_product

LIST_URL = "/api/products/"


def detail_url(product_id):
    return f"/api/products/{product_id}/"


def names(res):
    return {item["name"] for item in res.json()["results"]}


class ProductListTests(APITestCase):
    def test_fr1_list_pages_by_20_without_stopped(self):
        for i in range(22):
            make_product(name=f"판매 {i}")
        make_product(name="품절", sales_status=SalesStatus.SOLD_OUT)
        make_product(name="중지 1", sales_status=SalesStatus.STOPPED)
        make_product(name="중지 2", sales_status=SalesStatus.STOPPED)

        first = self.client.get(LIST_URL)
        second = self.client.get(LIST_URL, {"page": 2})

        self.assertEqual(first.status_code, 200)
        body = first.json()
        self.assertEqual(body["count"], 23)
        self.assertEqual(len(body["results"]), 20)
        self.assertEqual(body["next"], "/api/products/?page=2")
        all_names = names(first) | names(second)
        self.assertIn("품절", all_names)
        self.assertFalse({"중지 1", "중지 2"} & all_names)

    def test_fr1_list_is_public(self):
        make_product()
        res = self.client.get(LIST_URL)
        self.assertEqual(res.status_code, 200)

    def test_fr1_list_item_fields_and_newest_first(self):
        make_product(name="먼저")
        make_product(
            name="나중",
            base_price=15000,
            options=[
                {"weight_size": WeightSize.G500, "extra_price": 9000},
                {"weight_size": WeightSize.G200, "extra_price": 2000},
            ],
        )
        res = self.client.get(LIST_URL)
        first = res.json()["results"][0]
        self.assertEqual(first["name"], "나중")
        self.assertEqual(
            set(first),
            {
                "product_id",
                "name",
                "origin",
                "roast_level",
                "base_price",
                "lowest_price",
                "image_url",
                "sales_status",
            },
        )
        self.assertEqual(first["lowest_price"], 17000)

    def test_fr1_lowest_price_without_options_is_base_price(self):
        make_product(base_price=12000, options=[])
        res = self.client.get(LIST_URL)
        self.assertEqual(res.json()["results"][0]["lowest_price"], 12000)

    def test_fr1_page_out_of_range_is_404(self):
        make_product()
        res = self.client.get(LIST_URL, {"page": 5})
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()["code"], "NOT_FOUND")

    def test_fr2_search_by_name_part(self):
        make_product(name="에티오피아 예가체프")
        make_product(name="콜롬비아 수프리모")
        res = self.client.get(LIST_URL, {"search": " 에티 "})
        self.assertEqual(names(res), {"에티오피아 예가체프"})

    def test_fr3_filter_by_origin(self):
        make_product(name="A", origin="에티오피아")
        make_product(name="B", origin="케냐")
        res = self.client.get(LIST_URL, {"origin": "에티오피아"})
        self.assertEqual(names(res), {"A"})

    def test_fr4_filter_by_price_range(self):
        make_product(name="9999", base_price=9999)
        make_product(name="10000", base_price=10000)
        make_product(name="20000", base_price=20000)
        make_product(name="20001", base_price=20001)
        res = self.client.get(LIST_URL, {"min_price": 10000, "max_price": 20000})
        self.assertEqual(names(res), {"10000", "20000"})
        only_min = self.client.get(LIST_URL, {"min_price": 20000})
        self.assertEqual(names(only_min), {"20000", "20001"})

    def test_fr4_bad_price_param_is_400(self):
        for params in (
            {"min_price": "abc"},
            {"max_price": "-1"},
            {"min_price": 20000, "max_price": 10000},
        ):
            res = self.client.get(LIST_URL, params)
            self.assertEqual(res.status_code, 400, params)
            self.assertEqual(res.json()["code"], "VALIDATION_ERROR")

    def test_fr5_filter_by_roast_level(self):
        make_product(name="L", roast_level="LIGHT")
        make_product(name="D", roast_level="DARK")
        res = self.client.get(LIST_URL, {"roast_level": "LIGHT"})
        self.assertEqual(names(res), {"L"})
        bad = self.client.get(LIST_URL, {"roast_level": "BURNT"})
        self.assertEqual(bad.status_code, 400)

    def test_fr5_filters_combine_with_and(self):
        make_product(name="맞음", origin="케냐", roast_level="LIGHT", base_price=15000)
        make_product(name="원산지 틀림", origin="브라질", roast_level="LIGHT")
        make_product(name="로스팅 틀림", origin="케냐", roast_level="DARK")
        res = self.client.get(
            LIST_URL, {"origin": "케냐", "roast_level": "LIGHT", "max_price": 16000}
        )
        self.assertEqual(names(res), {"맞음"})


class ProductDetailTests(APITestCase):
    def test_fr6_detail_has_option_prices_and_availability(self):
        product = make_product(
            base_price=18000,
            tasting_notes="자스민, 레몬",
            options=[
                {"weight_size": WeightSize.KG1, "extra_price": 30000},
                {
                    "weight_size": WeightSize.G200,
                    "grind_type": GrindType.ESPRESSO,
                    "extra_price": 0,
                    "stock_quantity": 0,
                },
                {"weight_size": WeightSize.G200, "extra_price": 0},
            ],
        )
        res = self.client.get(detail_url(product.pk))
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["tasting_notes"], "자스민, 레몬")
        options = body["options"]
        self.assertEqual(
            [(o["weight_size"], o["grind_type"]) for o in options],
            [("200G", "WHOLE_BEAN"), ("200G", "ESPRESSO"), ("1KG", "WHOLE_BEAN")],
        )
        self.assertEqual([o["price"] for o in options], [18000, 18000, 48000])
        self.assertEqual([o["is_available"] for o in options], [True, False, True])
        self.assertEqual(
            set(options[0]),
            {
                "option_id",
                "weight_size",
                "grind_type",
                "extra_price",
                "price",
                "stock_quantity",
                "is_available",
            },
        )

    def test_dr8_sold_out_product_options_are_unavailable(self):
        product = make_product(sales_status=SalesStatus.SOLD_OUT)
        res = self.client.get(detail_url(product.pk))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["options"][0]["is_available"])

    def test_fr6_stopped_product_detail_is_404(self):
        product = make_product(sales_status=SalesStatus.STOPPED)
        res = self.client.get(detail_url(product.pk))
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()["code"], "NOT_FOUND")

    def test_fr6_unknown_product_is_404(self):
        res = self.client.get(detail_url(999999))
        self.assertEqual(res.status_code, 404)
