"""Test data builders for users (STP 1.2). No factory library."""

from itertools import count

from users.models import Role, User, UserAddress

_seq = count(1)


def make_member(email=None, password="pass1234", role=Role.MEMBER, **fields):
    n = next(_seq)
    fields.setdefault("user_name", f"member{n}")
    fields.setdefault("phone_number", "010-0000-0000")
    return User.objects.create_user(
        email=email or f"member{n}@example.com", password=password, role=role, **fields
    )


def make_address(user, is_default=False, **fields):
    fields.setdefault("recipient_name", "받는사람")
    fields.setdefault("recipient_phone", "010-1111-2222")
    fields.setdefault("zipcode", "28644")
    fields.setdefault("base_address", "충북 청주시 서원구 충대로 1")
    return UserAddress.objects.create(user=user, is_default=is_default, **fields)
