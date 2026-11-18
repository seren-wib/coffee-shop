"""Input checks for sign-up, login and profile (SDD 4.1). Messages are Korean (NFR-30)."""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from users.models import User, UserAddress

phone_validator = RegexValidator(
    r"^[0-9-]{1,20}$", "연락처는 숫자와 -만, 20자 이하로 입력해 주세요."
)
PRIVACY_REQUIRED = "개인정보 수집·이용에 동의해야 가입할 수 있습니다."


def _check_password(value, user=None):
    try:
        validate_password(value, user)
    except DjangoValidationError as e:
        raise serializers.ValidationError(list(e.messages))
    return value


class ProfileSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(max_length=20, validators=[phone_validator])

    class Meta:
        model = User
        fields = ["user_id", "email", "user_name", "phone_number", "role"]
        read_only_fields = ["user_id", "email", "role"]


class RegisterSerializer(serializers.Serializer):
    # No role field: whatever the request sends, sign-up makes a MEMBER (FR-7).
    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(write_only=True)
    user_name = serializers.CharField(max_length=100)
    phone_number = serializers.CharField(max_length=20, validators=[phone_validator])
    privacy_agreed = serializers.BooleanField(
        write_only=True, error_messages={"required": PRIVACY_REQUIRED}
    )

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("이미 가입된 이메일입니다.")
        return value

    def validate_password(self, value):
        return _check_password(value)

    def validate_privacy_agreed(self, value):
        if value is not True:
            raise serializers.ValidationError(PRIVACY_REQUIRED)
        return value


class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Only for showing the admin menu; the server checks the DB role (NFR-10).
        token["role"] = user.role
        return token

    def validate(self, attrs):
        attrs[self.username_field] = attrs[self.username_field].strip().lower()
        data = super().validate(attrs)
        data["user"] = {
            "user_id": self.user.user_id,
            "email": self.user.email,
            "user_name": self.user.user_name,
            "role": self.user.role,
        }
        return data


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("현재 비밀번호가 올바르지 않습니다.")
        return value

    def validate_new_password(self, value):
        return _check_password(value, self.context["request"].user)


zipcode_validator = RegexValidator(
    r"^[0-9]{5}$", "우편번호는 숫자 5자리로 입력해 주세요."
)


class AddressSerializer(serializers.ModelSerializer):
    recipient_phone = serializers.CharField(max_length=20, validators=[phone_validator])
    zipcode = serializers.CharField(max_length=10, validators=[zipcode_validator])
    is_default = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = UserAddress
        fields = [
            "address_id",
            "recipient_name",
            "recipient_phone",
            "zipcode",
            "base_address",
            "detail_address",
            "is_default",
        ]
        read_only_fields = ["address_id"]
        extra_kwargs = {"detail_address": {"required": False, "allow_blank": True}}
