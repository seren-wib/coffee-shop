from django.core.cache import cache
from rest_framework.test import APITestCase

from users.models import UserAddress
from users.tests.factories import make_address, make_member
from common.tests.helpers import auth_client

URL = "/api/me/addresses/"

NEW = {
    "recipient_name": "받는사람",
    "recipient_phone": "010-1111-2222",
    "zipcode": "28644",
    "base_address": "충북 청주시 서원구 충대로 1",
    "detail_address": "S4-1 101호",
}


class AddressApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_member()
        self.client = auth_client(self.user)

    def test_fr14_list_puts_default_first(self):
        make_address(self.user, is_default=False, recipient_name="둘째")
        make_address(self.user, is_default=True, recipient_name="기본")
        make_address(make_member(), is_default=True, recipient_name="남의것")
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual([a["recipient_name"] for a in body], ["기본", "둘째"])
        self.assertTrue(body[0]["is_default"])
        self.assertEqual(
            set(body[0]),
            {
                "address_id",
                "recipient_name",
                "recipient_phone",
                "zipcode",
                "base_address",
                "detail_address",
                "is_default",
            },
        )

    def test_fr15_create_first_address_is_default(self):
        res = self.client.post(URL, NEW, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json()["is_default"])
        missing = self.client.post(URL, {**NEW, "base_address": ""}, format="json")
        self.assertEqual(missing.status_code, 400)
        self.assertIn("base_address", missing.json()["fields"])

    def test_fr15_zipcode_must_be_five_digits(self):
        for bad in ("2864", "28644a", "286445"):
            res = self.client.post(URL, {**NEW, "zipcode": bad}, format="json")
            self.assertEqual(res.status_code, 400)
            self.assertIn("zipcode", res.json()["fields"])

    def test_fr16_update_address(self):
        address = make_address(self.user, is_default=True)
        res = self.client.patch(
            f"{URL}{address.address_id}/",
            {"recipient_name": "바뀐사람", "is_default": False},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["recipient_name"], "바뀐사람")
        address.refresh_from_db()
        self.assertTrue(address.is_default)

    def test_fr16_nfr11_other_members_address_is_404(self):
        theirs = make_address(make_member(), is_default=True)
        path = f"{URL}{theirs.address_id}/"
        self.assertEqual(
            self.client.patch(path, {"recipient_name": "x"}, format="json").status_code,
            404,
        )
        self.assertEqual(self.client.delete(path).status_code, 404)
        self.assertEqual(self.client.post(f"{path}default/").status_code, 404)
        self.assertTrue(UserAddress.objects.filter(pk=theirs.pk).exists())

    def test_fr17_delete_address(self):
        make_address(self.user, is_default=True)
        other = make_address(self.user, is_default=False)
        res = self.client.delete(f"{URL}{other.address_id}/")
        self.assertEqual(res.status_code, 204)
        self.assertFalse(UserAddress.objects.filter(pk=other.pk).exists())

    def test_fr17_delete_default_with_others_is_409(self):
        default = make_address(self.user, is_default=True)
        make_address(self.user, is_default=False)
        res = self.client.delete(f"{URL}{default.address_id}/")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "DEFAULT_ADDRESS_DELETE")

    def test_fr18_set_default(self):
        make_address(self.user, is_default=True)
        other = make_address(self.user, is_default=False)
        res = self.client.post(f"{URL}{other.address_id}/default/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["is_default"])
        self.assertEqual(
            list(
                UserAddress.objects.filter(user=self.user, is_default=True).values_list(
                    "address_id", flat=True
                )
            ),
            [other.address_id],
        )
