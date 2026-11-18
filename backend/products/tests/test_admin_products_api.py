from rest_framework.test import APITestCase

from orders.models import OrderItem
from orders.tests.factories import make_order
from products.models import GrindType, Product, ProductOption, SalesStatus, WeightSize
from products.tests.factories import make_product
from users.models import Role
from users.tests.factories import make_member
from common.tests.helpers import auth_client

LIST_URL = "/api/admin/products/"


def detail_url(pk):
    return f"/api/admin/products/{pk}/"


def options_url(pk):
    return f"/api/admin/products/{pk}/options/"


def option_url(pk, oid):
    return f"/api/admin/products/{pk}/options/{oid}/"


def _status(product):
    return Product.objects.values_list("sales_status", flat=True).get(pk=product.pk)


NEW_PRODUCT = {
    "name": "에티오피아 예가체프 G1",
    "origin": "에티오피아",
    "roast_level": "LIGHT",
    "base_price": 18000,
    "tasting_notes": "자스민, 레몬",
    "image_url": "https://images.example.com/yirgacheffe.jpg",
}


class AdminProductTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_member(role=Role.ADMIN)

    def setUp(self):
        self.client = auth_client(self.admin)


class AdminListTests(AdminProductTestCase):
    def test_fr36_list_includes_stopped(self):
        make_product(
            name="중지",
            sales_status=SalesStatus.STOPPED,
            options=[
                {"weight_size": WeightSize.G200, "stock_quantity": 3},
                {"weight_size": WeightSize.G500, "stock_quantity": 4},
            ],
        )
        make_product(name="판매")
        res = self.client.get(LIST_URL)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["count"], 2)
        stopped = next(p for p in body["results"] if p["name"] == "중지")
        self.assertEqual(stopped["sales_status"], "STOPPED")
        self.assertEqual(stopped["option_count"], 2)
        self.assertEqual(stopped["total_stock"], 7)
        self.assertEqual(
            set(stopped["options"][0]),
            {"option_id", "weight_size", "grind_type", "extra_price", "stock_quantity"},
        )

    def test_fr36_filter_by_sales_status(self):
        make_product(name="중지", sales_status=SalesStatus.STOPPED)
        make_product(name="판매")
        res = self.client.get(LIST_URL, {"sales_status": "STOPPED"})
        self.assertEqual([p["name"] for p in res.json()["results"]], ["중지"])
        bad = self.client.get(LIST_URL, {"sales_status": "GONE"})
        self.assertEqual(bad.status_code, 400)

    def test_fr36_product_without_options_has_zero_totals(self):
        make_product(options=[])
        item = self.client.get(LIST_URL).json()["results"][0]
        self.assertEqual((item["option_count"], item["total_stock"]), (0, 0))

    def test_fr56_search_by_name_part(self):
        make_product(name="에티오피아 구지", sales_status=SalesStatus.STOPPED)
        make_product(name="케냐 AA")
        res = self.client.get(LIST_URL, {"search": "에티"})
        self.assertEqual(
            [p["name"] for p in res.json()["results"]], ["에티오피아 구지"]
        )


class AdminCreateUpdateTests(AdminProductTestCase):
    def test_fr37_create_product_on_sale(self):
        res = self.client.post(LIST_URL, NEW_PRODUCT, format="json")
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(body["sales_status"], "ON_SALE")
        self.assertEqual(body["options"], [])
        self.assertIn("created_at", body)
        self.assertTrue(Product.objects.filter(pk=body["product_id"]).exists())

    def test_fr37_create_ignores_sales_status(self):
        res = self.client.post(
            LIST_URL, {**NEW_PRODUCT, "sales_status": "SOLD_OUT"}, format="json"
        )
        self.assertEqual(res.json()["sales_status"], "ON_SALE")

    def test_fr37_create_rejects_bad_input(self):
        cases = {
            "name": {k: v for k, v in NEW_PRODUCT.items() if k != "name"},
            "base_price": {**NEW_PRODUCT, "base_price": -1},
            "roast_level": {**NEW_PRODUCT, "roast_level": "BURNT"},
            "origin": {**NEW_PRODUCT, "origin": "화성"},
            "image_url": {
                **NEW_PRODUCT,
                "image_url": "http://images.example.com/a.jpg",
            },
        }
        for field, payload in cases.items():
            res = self.client.post(LIST_URL, payload, format="json")
            self.assertEqual(res.status_code, 400, field)
            self.assertIn(field, res.json()["fields"], field)
        self.assertEqual(Product.objects.count(), 0)

    def test_fr38_detail_for_edit_form(self):
        product = make_product(
            sales_status=SalesStatus.STOPPED, options=[{"extra_price": 2000}]
        )
        res = self.client.get(detail_url(product.pk))
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["sales_status"], "STOPPED")
        option = body["options"][0]
        self.assertEqual(option["price"], 20000)
        self.assertFalse(option["is_available"])
        self.assertEqual(self.client.get(detail_url(999999)).status_code, 404)

    def test_fr38_update_keeps_old_order_prices(self):
        product = make_product(base_price=18000)
        option = product.options.get()
        make_order(make_member(), option)
        res = self.client.patch(
            detail_url(product.pk),
            {"base_price": 21000, "name": "새 이름", "sales_status": "SOLD_OUT"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["options"][0]["price"], 21000)
        self.assertEqual(_status(product), SalesStatus.ON_SALE)
        item = OrderItem.objects.get(option=option)
        self.assertEqual((item.order_price, item.product_name), (18000, product.name))

    def test_fr38_update_rejects_origin_outside_list(self):
        product = make_product()
        res = self.client.patch(
            detail_url(product.pk), {"origin": "화성"}, format="json"
        )
        self.assertEqual(res.status_code, 400)


class AdminOptionTests(AdminProductTestCase):
    def test_fr39_add_option(self):
        product = make_product(options=[])
        res = self.client.post(
            options_url(product.pk),
            {
                "weight_size": "500G",
                "grind_type": "HAND_DRIP",
                "extra_price": 9000,
                "stock_quantity": 5,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        option = res.json()["options"][0]
        self.assertEqual((option["price"], option["stock_quantity"]), (27000, 5))

        dup = self.client.post(
            options_url(product.pk),
            {"weight_size": "500G", "grind_type": "HAND_DRIP", "stock_quantity": 1},
            format="json",
        )
        self.assertEqual(dup.status_code, 409)
        self.assertEqual(dup.json()["code"], "DUPLICATE_OPTION")

        neg = self.client.post(
            options_url(product.pk),
            {"weight_size": "1KG", "grind_type": "ESPRESSO", "extra_price": -1},
            format="json",
        )
        self.assertEqual(neg.status_code, 400)
        bad = self.client.post(
            options_url(product.pk),
            {"weight_size": "2KG", "grind_type": "ESPRESSO"},
            format="json",
        )
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(ProductOption.objects.filter(product=product).count(), 1)

    def test_fr39_first_option_with_zero_stock_marks_sold_out(self):
        product = make_product(options=[])
        res = self.client.post(
            options_url(product.pk),
            {"weight_size": "200G", "grind_type": "WHOLE_BEAN", "stock_quantity": 0},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["sales_status"], "SOLD_OUT")

    def test_fr39_add_option_to_unknown_product_is_404(self):
        res = self.client.post(
            options_url(999999),
            {"weight_size": "200G", "grind_type": "WHOLE_BEAN"},
            format="json",
        )
        self.assertEqual(res.status_code, 404)

    def test_fr40_update_option_extra_price(self):
        product = make_product(base_price=18000, options=[{"extra_price": 0}])
        option = product.options.get()
        res = self.client.patch(
            option_url(product.pk, option.pk), {"extra_price": 3000}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        public = self.client.get(f"/api/products/{product.pk}/").json()
        self.assertEqual(public["options"][0]["price"], 21000)

    def test_fr40_option_of_another_product_is_404(self):
        product = make_product()
        other = make_product().options.get()
        res = self.client.patch(
            option_url(product.pk, other.pk), {"extra_price": 3000}, format="json"
        )
        self.assertEqual(res.status_code, 404)

    def test_fr40_option_keeps_size_and_grind(self):
        product = make_product()
        option = product.options.get()
        self.client.patch(
            option_url(product.pk, option.pk),
            {"weight_size": "1KG", "grind_type": GrindType.ESPRESSO},
            format="json",
        )
        option.refresh_from_db()
        self.assertEqual(
            (option.weight_size, option.grind_type),
            (WeightSize.G200, GrindType.WHOLE_BEAN),
        )

    def test_fr41_stock_change_switches_sales_status(self):
        product = make_product(options=[{"stock_quantity": 2}])
        url = option_url(product.pk, product.options.get().pk)

        res = self.client.patch(url, {"stock_quantity": 0}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["sales_status"], "SOLD_OUT")

        res = self.client.patch(url, {"stock_quantity": 1}, format="json")
        self.assertEqual(res.json()["sales_status"], "ON_SALE")

        res = self.client.patch(url, {"stock_quantity": -1}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_fr40_fr41_price_and_stock_in_one_request(self):
        product = make_product(options=[{"stock_quantity": 2}])
        option = product.options.get()
        res = self.client.patch(
            option_url(product.pk, option.pk),
            {"extra_price": 1000, "stock_quantity": 7},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        option.refresh_from_db()
        self.assertEqual((option.extra_price, option.stock_quantity), (1000, 7))


class AdminSalesStatusTests(AdminProductTestCase):
    def test_fr42_stop_sales(self):
        product = make_product(options=[{"stock_quantity": 3}])
        res = self.client.post(f"{detail_url(product.pk)}stop/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["sales_status"], "STOPPED")

        self.client.patch(
            option_url(product.pk, product.options.get().pk),
            {"stock_quantity": 0},
            format="json",
        )
        self.assertEqual(_status(product), SalesStatus.STOPPED)

        again = self.client.post(f"{detail_url(product.pk)}stop/")
        self.assertEqual(again.status_code, 409)
        self.assertEqual(again.json()["code"], "INVALID_STATE")

    def test_fr43_resume_sales(self):
        in_stock = make_product(
            options=[{"stock_quantity": 3}], sales_status=SalesStatus.STOPPED
        )
        empty = make_product(
            options=[{"stock_quantity": 0}], sales_status=SalesStatus.STOPPED
        )
        res = self.client.post(f"{detail_url(in_stock.pk)}resume/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["sales_status"], "ON_SALE")
        res = self.client.post(f"{detail_url(empty.pk)}resume/")
        self.assertEqual(res.json()["sales_status"], "SOLD_OUT")
        again = self.client.post(f"{detail_url(in_stock.pk)}resume/")
        self.assertEqual(again.status_code, 409)
