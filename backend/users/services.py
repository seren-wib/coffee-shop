"""Member rules (SDD 4.1, 4.2). Views and serializers call these; they hold no rules."""

from django.db import transaction
from django.utils import timezone

from users.models import Role, User


@transaction.atomic
def register_member(*, email, password, user_name, phone_number):
    """Sign-up always makes a MEMBER and records the privacy consent time (FR-7, FR-58)."""
    return User.objects.create_user(
        email=email,
        password=password,
        user_name=user_name,
        phone_number=phone_number,
        role=Role.MEMBER,
        privacy_agreed_at=timezone.now(),
    )


def change_password(user, new_password):
    user.set_password(new_password)
    user.save(update_fields=["password"])
