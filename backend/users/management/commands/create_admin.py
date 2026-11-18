"""python manage.py create_admin --email <email> (SDD 4.9.2, FR-53).

The password is read twice with getpass, never taken as an argument, so it stays out of
shell history and the process list. createsuperuser is not used: it does not set role.
"""

import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from users.models import Role, User


class Command(BaseCommand):
    help = "Create an ADMIN account, or promote an existing account to ADMIN."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", default="관리자")
        parser.add_argument("--phone", default="")

    def handle(self, *args, email, name, phone, **options):
        email = email.strip().lower()
        existing = User.objects.filter(email=email).first()
        if existing:
            answer = input(f"{email} already exists. Make it ADMIN? [y/N] ")
            if answer.strip().lower() != "y":
                self.stdout.write("Unchanged.")
                return
            existing.role = Role.ADMIN
            existing.save(update_fields=["role"])
            self.stdout.write(f"{email} is now ADMIN.")
            return

        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Password (again): "):
            raise CommandError("Passwords do not match.")
        try:
            validate_password(password)
        except ValidationError as e:
            raise CommandError(" ".join(e.messages))
        User.objects.create_user(
            email=email,
            password=password,
            user_name=name,
            phone_number=phone,
            role=Role.ADMIN,
        )
        self.stdout.write(f"Created ADMIN {email}.")
