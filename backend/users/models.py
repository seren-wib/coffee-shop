from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class Role(models.TextChoices):
    MEMBER = "MEMBER", "Member"
    ADMIN = "ADMIN", "Admin"


class User(models.Model):
    user_id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True, max_length=255)
    password_hash = models.CharField(max_length=255)
    user_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_name} ({self.email})"

    @classmethod
    def register(cls, email, password, user_name, phone_number, role=Role.MEMBER):
        return cls.objects.create(
            email=email,
            password_hash=make_password(password),
            user_name=user_name,
            phone_number=phone_number,
            role=role,
        )

    def login(self, password: str) -> bool:
        return check_password(password, self.password_hash)

    def update_profile(self, name: str, phone: str):
        self.user_name = name
        self.phone_number = phone
        self.save(update_fields=["user_name", "phone_number"])

    def change_password(self, old_pw: str, new_pw: str) -> bool:
        if not self.login(old_pw):
            return False
        self.password_hash = make_password(new_pw)
        self.save(update_fields=["password_hash"])
        return True


class UserAddress(models.Model):
    address_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="addresses", db_column="user_id"
    )
    recipient_name = models.CharField(max_length=100)
    recipient_phone = models.CharField(max_length=20)
    zipcode = models.CharField(max_length=10)
    base_address = models.CharField(max_length=255)
    detail_address = models.CharField(max_length=255, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_addresses"
        indexes = [
            models.Index(fields=["user"], name="idx_user_addresses_user_id"),
        ]

    def __str__(self):
        return f"{self.recipient_name} - {self.base_address}"

    def set_default(self):
        UserAddress.objects.filter(user=self.user).exclude(pk=self.pk).update(
            is_default=False
        )
        self.is_default = True
        self.save(update_fields=["is_default"])

    def update_address(
        self,
        recipient_name=None,
        recipient_phone=None,
        zipcode=None,
        base_address=None,
        detail_address=None,
        is_default=None,
    ):
        if recipient_name is not None:
            self.recipient_name = recipient_name
        if recipient_phone is not None:
            self.recipient_phone = recipient_phone
        if zipcode is not None:
            self.zipcode = zipcode
        if base_address is not None:
            self.base_address = base_address
        if detail_address is not None:
            self.detail_address = detail_address
        if is_default is not None:
            self.is_default = is_default
            if is_default:
                UserAddress.objects.filter(user=self.user).exclude(pk=self.pk).update(
                    is_default=False
                )
        self.save()
