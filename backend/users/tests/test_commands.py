from io import StringIO
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase

from common.tests.helpers import auth_client
from users.models import Role, User
from users.tests.factories import make_member


def _run(*args, passwords=("adminpass1", "adminpass1"), answer="y"):
    with (
        mock.patch(
            "users.management.commands.create_admin.getpass.getpass",
            side_effect=list(passwords),
        ),
        mock.patch("builtins.input", return_value=answer),
    ):
        call_command("create_admin", *args, stdout=StringIO())


class CreateAdminTests(TestCase):
    def test_fr53_create_admin_command(self):
        _run("--email", "Boss@Example.com")
        user = User.objects.get(email="boss@example.com")
        self.assertEqual(user.role, Role.ADMIN)
        self.assertTrue(user.check_password("adminpass1"))
        self.assertIsNone(user.privacy_agreed_at)

    def test_fr53_created_admin_can_use_admin_routes(self):
        _run("--email", "boss@example.com")
        client = auth_client(User.objects.get(email="boss@example.com"), "adminpass1")
        self.assertEqual(client.get("/api/admin/orders/").status_code, 200)

    def test_fr53_rejects_short_or_mismatched_password(self):
        with self.assertRaises(CommandError):
            _run("--email", "a@example.com", passwords=("short1", "short1"))
        with self.assertRaises(CommandError):
            _run("--email", "a@example.com", passwords=("adminpass1", "adminpass2"))
        self.assertFalse(User.objects.filter(email="a@example.com").exists())

    def test_fr53_promotes_existing_member_after_confirmation(self):
        make_member(email="m@example.com", password="pass1234")
        _run("--email", "m@example.com", answer="y")
        user = User.objects.get(email="m@example.com")
        self.assertEqual(user.role, Role.ADMIN)
        self.assertTrue(user.check_password("pass1234"))

    def test_fr53_keeps_existing_member_when_declined(self):
        make_member(email="m@example.com")
        _run("--email", "m@example.com", answer="n")
        self.assertEqual(User.objects.get(email="m@example.com").role, Role.MEMBER)
