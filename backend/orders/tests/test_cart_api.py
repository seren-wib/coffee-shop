from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

from common.tests.helpers import auth_client
from orders.models import CartItem
from products.models import ProductOption, SalesStatus
from products.tests.factories import make_product
from users.tests.factories import make_member

ITEMS = "/api/cart/items/"
CART = "/api/cart/"


class CartApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_member()
        self.client = auth_client(self.user)
        self.option = make_product(
            base_price=14500, options=[{"stock_quantity": 5}]
        ).options.get()

    def _add(self, option, quantity=1, client=None):
        return (client or self.client).post(
            ITEMS, {"option_id": option.option_id, "quantity": quantity}, format="json"
        )

    def test_fr19_add_item(self):
        first = self._add(self.option, 1)
        again = self._add(self.option, 2)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json()["quantity"], 3)
        self.assertEqual(set(again.json()), {"cart_item_id", "option_id", "quantity"})
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 1)

    def test_fr19_unavailable_option_is_409(self):
        product = make_product(
            options=[
                {"stock_quantity": 0},
                {"stock_quantity": 5, "weight_size": "500G"},
            ]
        )
        empty = product.options.get(stock_quantity=0)
        stopped = make_product(sales_status=SalesStatus.STOPPED).options.get()
        res = self._add(empty)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "OUT_OF_STOCK")
        res = self._add(stopped)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "NOT_AVAILABLE")

    def test_fr19_rejects_missing_option_and_bad_quantity(self):
        res = self.client.post(
            ITEMS, {"option_id": 999999, "quantity": 1}, format="json"
        )
        self.assertEqual(res.status_code, 404)
        res = self._add(self.option, 0)
        self.assertEqual(res.status_code, 400)
        self.assertIn("quantity", res.json()["fields"])

    def test_fr19_needs_token(self):
        res = self._add(self.option, client=APIClient())
        self.assertEqual(res.status_code, 401)

    def test_fr20_cart_totals(self):
        self._add(self.option, 2)  # 29,000
        res = self.client.get(CART)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        item = body["items"][0]
        self.assertEqual(item["price"], 14500)
        self.assertEqual(item["subtotal"], 29000)
        self.assertTrue(item["is_available"])
        self.assertEqual(body["product_amount"], 29000)
        self.assertEqual(body["shipping_fee"], 3000)
        self.assertEqual(body["total_amount"], 32000)
        self.assertTrue(body["can_order"])

        extra = make_product(base_price=1000).options.get()
        self._add(extra, 1)  # 30,000
        body = self.client.get(CART).json()
        self.assertEqual(body["product_amount"], 30000)
        self.assertEqual(body["shipping_fee"], 0)
        self.assertEqual(body["total_amount"], 30000)

    def test_fr20_item_fields_and_unavailable_items(self):
        self._add(self.option, 3)
        ProductOption.objects.filter(pk=self.option.pk).update(stock_quantity=2)
        body = self.client.get(CART).json()
        item = body["items"][0]
        self.assertEqual(
            set(item),
            {
                "cart_item_id",
                "option_id",
                "product_id",
                "product_name",
                "image_url",
                "weight_size",
                "grind_type",
                "price",
                "quantity",
                "subtotal",
                "stock_quantity",
                "is_available",
            },
        )
        self.assertFalse(item["is_available"])
        self.assertFalse(body["can_order"])

    def test_fr20_empty_cart(self):
        body = self.client.get(CART).json()
        self.assertEqual(body["items"], [])
        self.assertEqual(body["shipping_fee"], 0)
        self.assertFalse(body["can_order"])

    def test_fr20_lists_items_in_added_order_and_only_mine(self):
        second = make_product().options.get()
        self._add(self.option)
        self._add(second)
        other = make_member()
        self._add(self.option, client=auth_client(other))
        ids = [i["option_id"] for i in self.client.get(CART).json()["items"]]
        self.assertEqual(ids, [self.option.option_id, second.option_id])

    def test_fr21_change_quantity(self):
        item_id = self._add(self.option, 1).json()["cart_item_id"]
        path = f"{ITEMS}{item_id}/"
        res = self.client.patch(path, {"quantity": 4}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["quantity"], 4)
        res = self.client.patch(path, {"quantity": 0}, format="json")
        self.assertEqual(res.status_code, 400)
        res = self.client.patch(path, {"quantity": 6}, format="json")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "OUT_OF_STOCK")
        self.assertEqual(CartItem.objects.get(pk=item_id).quantity, 4)

    def test_fr22_remove_item(self):
        item_id = self._add(self.option).json()["cart_item_id"]
        res = self.client.delete(f"{ITEMS}{item_id}/")
        self.assertEqual(res.status_code, 204)
        self.assertEqual(self.client.get(CART).json()["items"], [])

    def test_nfr11_other_members_cart_item_is_404(self):
        theirs = self._add(self.option, client=auth_client(make_member()))
        path = f"{ITEMS}{theirs.json()['cart_item_id']}/"
        self.assertEqual(
            self.client.patch(path, {"quantity": 2}, format="json").status_code, 404
        )
        self.assertEqual(self.client.delete(path).status_code, 404)
        self.assertEqual(CartItem.objects.count(), 1)
