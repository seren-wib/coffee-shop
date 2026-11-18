from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from users.models import Role
from users.tests.factories import make_address, make_member


class UserModelTests(TestCase):
    def test_fr7_auth_user_model_is_users_user(self):
        self.assertEqual(get_user_model()._meta.label, "users.User")

    def test_fr7_create_user_lowercases_email_and_defaults_to_member(self):
        user = make_member(email="Kim@Example.COM")
        self.assertEqual(user.email, "kim@example.com")
        self.assertEqual(user.role, Role.MEMBER)
        self.assertTrue(user.is_active)
        self.assertIsNone(user.privacy_agreed_at)

    def test_fr8_email_is_the_login_id(self):
        make_member(email="lee@example.com", password="pass1234")
        self.assertIsNotNone(authenticate(email="lee@example.com", password="pass1234"))
        self.assertIsNone(authenticate(email="lee@example.com", password="wrong123"))

    def test_fr7_email_is_unique(self):
        make_member(email="dup@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_member(email="DUP@example.com")

    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.PBKDF2PasswordHasher"]
    )
    def test_nfr6_password_stored_as_pbkdf2_hash(self):
        user = make_member(password="pass1234")
        self.assertTrue(user.password.startswith("pbkdf2_sha256$"))
        self.assertNotIn("pass1234", user.password)

    def test_nfr10_role_check_constraint(self):
        user = make_member()
        user.role = "ROOT"
        with self.assertRaises(IntegrityError), transaction.atomic():
            user.save()

    def test_nfr10_is_staff_follows_role(self):
        self.assertFalse(make_member().is_staff)
        self.assertTrue(make_member(role=Role.ADMIN).is_staff)


class UserAddressModelTests(TestCase):
    def test_dr16_db_allows_one_default_address_per_member(self):
        user = make_member()
        make_address(user, is_default=True)
        make_address(user, is_default=False)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_address(user, is_default=True)

    def test_dr16_other_members_have_their_own_default(self):
        make_address(make_member(), is_default=True)
        make_address(make_member(), is_default=True)
