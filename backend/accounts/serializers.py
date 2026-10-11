"""API serializers for users: register, login (JWT), and "who am I"."""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Public view of a user (never includes the password)."""

    department_name = serializers.CharField(source="department.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "department", "department_name"]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    """Student sign-up through the API. Same rules as the HTML form."""

    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password"]
        extra_kwargs = {"email": {"required": True}, "first_name": {"required": True}}

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        # Run Django's password rules (length, common passwords, ...).
        validate_password(attrs["password"], user=User(username=attrs.get("username"), email=attrs.get("email")))
        return attrs

    def create(self, validated_data):
        # create_user hashes the password. Role is always student; "role" is not even a field here.
        return User.objects.create_user(role=User.Role.STUDENT, **validated_data)


class CampusTokenSerializer(TokenObtainPairSerializer):
    """
    Login: checks username + password and returns access/refresh tokens.
    We add role and username inside the token, and the user object in the
    response, so the React app knows which pages to show.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
