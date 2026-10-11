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


# --- ML helpers (Phase 4) -------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_ai(tmp_path, monkeypatch):
    """
    Every test: no real LLM calls (LLM_PROVIDER=none) and an empty, temporary
    models folder, so tests never depend on (or overwrite) locally trained files.
    """
    import ai.llm_client

    monkeypatch.setenv("LLM_PROVIDER", "none")
    monkeypatch.setenv("ML_ARTIFACT_DIR", str(tmp_path / "ml"))
    monkeypatch.setattr(ai.llm_client, "_client", None)


@pytest.fixture
def ml_dir():
    """The temporary folder where tests save trained models."""
    from ai.ml.common import artifact_dir

    return artifact_dir()


@pytest.fixture
def saved_classifier(ml_dir, trained_classifier):
    """A trained classifier saved where the app looks for it."""
    from ai.ml import train_classifier

    train_classifier.save(trained_classifier)
    return trained_classifier


@pytest.fixture(scope="session")
def sample_rows():
    from ai.ml.common import SAMPLE_CSV, load_rows

    return load_rows([SAMPLE_CSV])


@pytest.fixture(scope="session")
def trained_classifier(sample_rows):
    """One classifier trained on the synthetic CSV, shared by all tests (training takes ~1s)."""
    from ai.ml import train_classifier

    return train_classifier.train(sample_rows)


# --- Fake LLM (Phase 5) -----------------------------------------------------------

class FakeLLM:
    """
    Stands in for LLMClient in tests. Give it a list of replies: a string is returned
    as the reply text, an Exception is raised. It records every call.
    """

    enabled = True

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def create(self, **kwargs):
        from ai.llm_client import LLMReply

        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        if isinstance(reply, LLMReply):
            return reply
        return LLMReply(text=reply, stop_reason="end_turn", model="fake-model")


@pytest.fixture
def fake_llm(monkeypatch):
    """fake_llm(replies) -> installs a FakeLLM as the app's LLM client and returns it."""
    import ai.llm_client

    def install(replies):
        fake = FakeLLM(replies)
        monkeypatch.setattr(ai.llm_client, "_client", fake)
        return fake

    return install
