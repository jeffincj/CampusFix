"""Shared pytest fixtures: users of each role and a sample complaint."""
import pytest

from accounts.models import User
from complaints import services
from complaints.models import Department

PASSWORD = "Strong-Pass-123"


@pytest.fixture
def hostel():
    # Departments are created by the 0002_seed_departments migration.
    return Department.objects.get(code="HOSTEL")


@pytest.fixture
def it_dept():
    return Department.objects.get(code="IT")


@pytest.fixture
def student(db):
    return User.objects.create_user("student1", "s1@college.edu", PASSWORD)


@pytest.fixture
def other_student(db):
    return User.objects.create_user("student2", "s2@college.edu", PASSWORD)


@pytest.fixture
def hostel_staff(hostel):
    return User.objects.create_user("warden", "warden@college.edu", PASSWORD, role=User.Role.STAFF, department=hostel)


@pytest.fixture
def it_staff(it_dept):
    return User.objects.create_user("itguy", "it@college.edu", PASSWORD, role=User.Role.STAFF, department=it_dept)


@pytest.fixture
def admin_user(db):
    return User.objects.create_user("principal", "admin@college.edu", PASSWORD, role=User.Role.ADMIN)


@pytest.fixture
def complaint(student):
    """An open hostel complaint created through the service (so history is written)."""
    return services.create_complaint(
        student,
        title="Fan not working",
        description="The ceiling fan in my room is not working since Monday.",
        category="HOSTEL",
        location="Room 214",
        block="B Block",
    )


# --- API helpers (Phase 3) ------------------------------------------------------

@pytest.fixture
def api():
    """A DRF test client with no login."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def api_as():
    """
    api_as(user) -> APIClient that sends a real JWT access token for that user,
    exactly like the React app will (Authorization: Bearer <token>).
    """
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    def make(user):
        client = APIClient()
        token = RefreshToken.for_user(user).access_token
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    return make
