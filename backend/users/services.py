"""Member rules (SDD 4.1, 4.2). Views and serializers call these; they hold no rules."""

from django.db import transaction
from django.utils import timezone

from common.exceptions import DomainError
from users.models import Role, User, UserAddress


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


# Addresses (SDD 4.2). The partial unique index blocks two defaults; these functions
# make sure a member with addresses never has zero (DR-16, DR-17).


def _own_address(user, address_id):
    # Filter by owner first: another member's ID looks the same as a missing one (NFR-11).
    address = UserAddress.objects.filter(user=user, address_id=address_id).first()
    if address is None:
        raise DomainError("NOT_FOUND", "찾을 수 없습니다.", 404)
    return address


def _clear_default(user):
    UserAddress.objects.filter(user=user, is_default=True).update(is_default=False)


@transaction.atomic
def create_address(user, *, is_default=False, **fields):
    if not UserAddress.objects.filter(user=user).exists():
        is_default = True
    elif is_default:
        _clear_default(user)
    return UserAddress.objects.create(user=user, is_default=is_default, **fields)


@transaction.atomic
def update_address(user, address_id, **fields):
    # is_default is not accepted here: set it with set_default_address (SDD 4.2.3).
    fields.pop("is_default", None)
    address = _own_address(user, address_id)
    for name, value in fields.items():
        setattr(address, name, value)
    address.save(update_fields=list(fields) or None)
    return address


@transaction.atomic
def set_default_address(user, address_id):
    address = _own_address(user, address_id)
    # Clear first, then set, or the partial unique index rejects the second default.
    _clear_default(user)
    UserAddress.objects.filter(pk=address.pk).update(is_default=True)
    address.is_default = True
    return address


@transaction.atomic
def delete_address(user, address_id):
    address = _own_address(user, address_id)
    if (
        address.is_default
        and UserAddress.objects.filter(user=user).exclude(pk=address.pk).exists()
    ):
        raise DomainError(
            "DEFAULT_ADDRESS_DELETE", "다른 배송지를 먼저 기본으로 정해 주세요.", 409
        )
    address.delete()
