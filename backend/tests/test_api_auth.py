"""Phase 3 tests: JWT register / login / refresh / me."""
import pytest
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User

pytestmark = pytest.mark.django_db

SIGNUP = {"username": "ravi", "email": "Ravi@College.edu", "first_name": "Ravi", "password": "Strong-Pass-123"}


def test_register_creates_student(api):
    response = api.post("/api/auth/register/", SIGNUP, format="json")
    assert response.status_code == 201
    assert response.data["role"] == "student"
    assert response.data["email"] == "ravi@college.edu"
    assert "password" not in response.data
    assert User.objects.get(username="ravi").check_password("Strong-Pass-123")


def test_register_ignores_role_field(api):
    api.post("/api/auth/register/", {**SIGNUP, "role": "admin"}, format="json")
    assert User.objects.get(username="ravi").role == "student"


def test_register_validation_errors(api, student):
    response = api.post("/api/auth/register/", {**SIGNUP, "email": student.email, "password": "123"}, format="json")
    assert response.status_code == 400
    assert "email" in response.data


def test_register_weak_password(api):
    response = api.post("/api/auth/register/", {**SIGNUP, "password": "password"}, format="json")
    assert response.status_code == 400


def test_login_returns_tokens_with_role(api, hostel_staff):
    response = api.post("/api/auth/login/", {"username": "warden", "password": "Strong-Pass-123"}, format="json")
    assert response.status_code == 200
    assert {"access", "refresh", "user"} <= set(response.data)
    assert response.data["user"]["role"] == "staff"
    assert response.data["user"]["department_name"] == "Hostel Office"
    claims = AccessToken(response.data["access"])
    assert claims["role"] == "staff" and claims["username"] == "warden"


def test_login_wrong_password(api, student):
    response = api.post("/api/auth/login/", {"username": student.username, "password": "nope"}, format="json")
    assert response.status_code == 401


def test_refresh_gives_new_access_token(api, student):
    tokens = api.post("/api/auth/login/", {"username": student.username, "password": "Strong-Pass-123"}, format="json").data
    response = api.post("/api/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert response.status_code == 200
    assert "access" in response.data


def test_me_with_token(api, student):
    access = api.post("/api/auth/login/", {"username": student.username, "password": "Strong-Pass-123"}, format="json").data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = api.get("/api/auth/me/")
    assert response.status_code == 200
    assert response.data["username"] == student.username


def test_protected_endpoints_need_token(api):
    assert api.get("/api/auth/me/").status_code == 401
    assert api.get("/api/complaints/").status_code == 401


def test_bad_token_rejected(api):
    api.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
    assert api.get("/api/complaints/").status_code == 401


def test_login_is_rate_limited(api, monkeypatch):
    from django.core.cache import cache
    from rest_framework.throttling import ScopedRateThrottle

    cache.clear()  # throttle counters live in the cache
    # Lower the limit just for this test (monkeypatch restores it afterwards).
    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"auth": "3/min"})
    codes = [api.post("/api/auth/login/", {"username": "x", "password": "y"}, format="json").status_code for _ in range(4)]
    cache.clear()
    assert codes == [401, 401, 401, 429]
