from django.test import TestCase

from common.exceptions import DomainError
from users import services
from users.models import UserAddress
from users.tests.factories import make_member

ADDRESS = {
    "recipient_name": "받는사람",
    "recipient_phone": "010-1111-2222",
    "zipcode": "28644",
    "base_address": "충북 청주시 서원구 충대로 1",
}


class AddressServiceTests(TestCase):
    def setUp(self):
        self.user = make_member()

    def _defaults(self):
        return list(
            UserAddress.objects.filter(user=self.user, is_default=True).values_list(
                "address_id", flat=True
            )
        )

    def test_dr16_first_address_becomes_default(self):
        first = services.create_address(self.user, is_default=False, **ADDRESS)
        second = services.create_address(self.user, is_default=False, **ADDRESS)
        self.assertTrue(first.is_default)
        self.assertFalse(second.is_default)

    def test_dr16_new_default_replaces_old_one(self):
        services.create_address(self.user, **ADDRESS)
        new = services.create_address(self.user, is_default=True, **ADDRESS)
        self.assertEqual(self._defaults(), [new.address_id])

    def test_dr16_set_default_leaves_exactly_one(self):
        services.create_address(self.user, **ADDRESS)
        other = services.create_address(self.user, **ADDRESS)
        result = services.set_default_address(self.user, other.address_id)
        self.assertTrue(result.is_default)
        self.assertEqual(self._defaults(), [other.address_id])

    def test_dr17_default_delete_blocked_while_others_exist(self):
        first = services.create_address(self.user, **ADDRESS)
        second = services.create_address(self.user, **ADDRESS)
        with self.assertRaises(DomainError) as ctx:
            services.delete_address(self.user, first.address_id)
        self.assertEqual(ctx.exception.code, "DEFAULT_ADDRESS_DELETE")
        self.assertEqual(ctx.exception.status, 409)
        services.delete_address(self.user, second.address_id)
        services.delete_address(self.user, first.address_id)
        self.assertFalse(UserAddress.objects.filter(user=self.user).exists())

    def test_nfr11_other_members_address_is_not_found(self):
        mine = services.create_address(self.user, **ADDRESS)
        stranger = make_member()
        for call in (services.set_default_address, services.delete_address):
            with self.assertRaises(DomainError) as ctx:
                call(stranger, mine.address_id)
            self.assertEqual(ctx.exception.status, 404)
