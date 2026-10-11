"""Phase 1 tests: custom user roles, registration, login, logout, page access."""
import pytest
from django.urls import reverse

from accounts.models import User

# Every test in this file may use the (SQLite test) database.
pytestmark = pytest.mark.django_db

VALID_SIGNUP = {
    "username": "priya",
    "first_name": "Priya",
    "last_name": "S",
    "email": "Priya@College.edu",
    "password1": "Strong-Pass-123",
    "password2": "Strong-Pass-123",
}


# --- User model / roles -------------------------------------------------------

def test_new_user_defaults_to_student():
    user = User.objects.create_user("arun", "arun@college.edu", "Strong-Pass-123")
    assert user.role == User.Role.STUDENT
    assert user.is_student and not user.is_staff_member and not user.is_admin


def test_superuser_is_always_admin():
    user = User.objects.create_superuser("boss", "boss@college.edu", "Strong-Pass-123")
    assert user.role == User.Role.ADMIN
    assert user.is_admin


def test_staff_role_helper():
    user = User.objects.create_user("meena", "meena@college.edu", "Strong-Pass-123", role=User.Role.STAFF)
    assert user.is_staff_member
    assert not user.is_staff  # Django admin access is separate from our staff role


def test_users_table_name():
    assert User._meta.db_table == "users"


# --- Registration -------------------------------------------------------------

def test_register_page_loads(client):
    response = client.get(reverse("web:register"))
    assert response.status_code == 200
    assert b"Student registration" in response.content


def test_register_creates_student_and_logs_in(client):
    response = client.post(reverse("web:register"), VALID_SIGNUP)
    assert response.status_code == 302
    assert response.url == reverse("web:dashboard")

    user = User.objects.get(username="priya")
    assert user.role == User.Role.STUDENT
    assert user.email == "priya@college.edu"  # stored lowercase
    # The session now belongs to the new user.
    assert int(client.session["_auth_user_id"]) == user.pk


def test_register_cannot_choose_admin_role(client):
    """A tampered POST with role=admin must still create a student."""
    data = {**VALID_SIGNUP, "role": "admin"}
    client.post(reverse("web:register"), data)
    assert User.objects.get(username="priya").role == User.Role.STUDENT


def test_register_rejects_duplicate_email(client):
    User.objects.create_user("old", "priya@college.edu", "Strong-Pass-123")
    response = client.post(reverse("web:register"), VALID_SIGNUP)
    assert response.status_code == 200  # form shown again with errors
    assert b"already exists" in response.content
    assert not User.objects.filter(username="priya").exists()


def test_register_rejects_mismatched_passwords(client):
    data = {**VALID_SIGNUP, "password2": "Different-Pass-999"}
    response = client.post(reverse("web:register"), data)
    assert response.status_code == 200
    assert not User.objects.filter(username="priya").exists()


def test_register_rejects_weak_password(client):
    data = {**VALID_SIGNUP, "password1": "12345678", "password2": "12345678"}
    response = client.post(reverse("web:register"), data)
    assert response.status_code == 200
    assert not User.objects.filter(username="priya").exists()


# --- Login / logout -----------------------------------------------------------

def test_login_success_redirects_to_dashboard(client):
    User.objects.create_user("arun", "arun@college.edu", "Strong-Pass-123")
    response = client.post(reverse("web:login"), {"username": "arun", "password": "Strong-Pass-123"})
    assert response.status_code == 302
    assert response.url == reverse("web:dashboard")


def test_login_wrong_password_fails(client):
    User.objects.create_user("arun", "arun@college.edu", "Strong-Pass-123")
    response = client.post(reverse("web:login"), {"username": "arun", "password": "wrong-password"})
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


def test_logout_requires_post_and_logs_out(client):
    user = User.objects.create_user("arun", "arun@college.edu", "Strong-Pass-123")
    client.force_login(user)
    assert client.get(reverse("web:logout")).status_code == 405  # GET not allowed
    response = client.post(reverse("web:logout"))
    assert response.status_code == 302
    assert "_auth_user_id" not in client.session


# --- Page access by role ------------------------------------------------------

def test_dashboard_requires_login(client):
    response = client.get(reverse("web:dashboard"))
    assert response.status_code == 302
    assert reverse("web:login") in response.url


@pytest.mark.parametrize(
    "role, expected_text",
    [
        (User.Role.STUDENT, b"+ New complaint"),
        (User.Role.STAFF, b"signed in as <strong>staff</strong>"),
        (User.Role.ADMIN, b"signed in as <strong>admin</strong>"),
    ],
)
def test_dashboard_shows_role_specific_content(client, role, expected_text):
    user = User.objects.create_user(f"user_{role}", f"{role}@college.edu", "Strong-Pass-123", role=role)
    client.force_login(user)
    response = client.get(reverse("web:dashboard"))
    assert response.status_code == 200
    assert expected_text in response.content


def test_logged_in_user_skips_home_and_login(client):
    user = User.objects.create_user("arun", "arun@college.edu", "Strong-Pass-123")
    client.force_login(user)
    assert client.get(reverse("web:home")).url == reverse("web:dashboard")
    assert client.get(reverse("web:login")).status_code == 302
    assert client.get(reverse("web:register")).url == reverse("web:dashboard")
