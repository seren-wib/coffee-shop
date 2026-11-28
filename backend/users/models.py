"""Members and their addresses (SDD 6.1, 6.2). Rules that change rows live in services."""

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.db.models import Q


class Role(models.TextChoices):
    MEMBER = "MEMBER", "Member"
    ADMIN = "ADMIN", "Admin"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **fields):
        if not email:
            raise ValueError("email is required")
        user = self.model(email=email.strip().lower(), **fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.AutoField(primary_key=True)
    email = models.EmailField(max_length=255, unique=True)
    user_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    is_active = models.BooleanField(default=True)
    privacy_agreed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["user_name", "phone_number"]

    class Meta:
        db_table = "users"
        constraints = [
            models.CheckConstraint(
                condition=Q(role__in=Role.values), name="ck_users_role"
            ),
        ]

    def __str__(self):
        return self.email

    @property
    def is_staff(self):
        # Only the development /admin/ site reads this (SDD 6.1).
        return self.role == Role.ADMIN


class UserAddress(models.Model):
    address_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    recipient_name = models.CharField(max_length=100)
    recipient_phone = models.CharField(max_length=20)
    zipcode = models.CharField(max_length=10)
    base_address = models.CharField(max_length=255)
    detail_address = models.CharField(max_length=255, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_addresses"
        indexes = [models.Index(fields=["user"], name="idx_user_addresses_user_id")]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_default=True),
                name="uq_user_addresses_one_default",
            ),
        ]

    def __str__(self):
        return f"{self.recipient_name} - {self.base_address}"
