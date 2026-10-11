"""Phase 5 tests: embeddings, FAISS search and duplicate linking."""
import numpy as np
import pytest

from ai import embeddings
from ai.pipeline import submit_complaint
from complaints import services
from complaints.models import DuplicateLink

pytestmark = pytest.mark.django_db


def cosine(a, b):
    return float(np.dot(embeddings.embed_text(a), embeddings.embed_text(b)))


def test_embeddings_are_normalised():
    vector = embeddings.embed_text("Wi-Fi not working")
    assert vector.dtype == np.float32
    assert np.linalg.norm(vector) == pytest.approx(1.0, abs=1e-5)


def test_similarity_near_duplicates_high_unrelated_low():
    assert cosine("Wi-Fi not working in B Block Hostel", "wifi not working in b block hostel!!") > 0.95
    assert cosine("வைஃபை வேலை செய்யவில்லை", "வைஃபை வேலை செய்யவில்லை இன்று") > 0.85
    assert cosine("Wi-Fi not working in B Block Hostel", "Bus number 7 broke down on the highway") < 0.5


def test_bytes_round_trip():
    vector = embeddings.embed_text("fan broken")
    assert np.array_equal(embeddings.from_bytes(embeddings.to_bytes(vector)), vector)


def test_faiss_index_returns_most_similar():
    vectors = [embeddings.embed_text(t) for t in ["bus late", "wifi not working", "food is cold"]]
    index = embeddings.build_index(vectors)
    scores, positions = index.search(np.asarray([embeddings.embed_text("wifi is not working")]), 1)
    assert positions[0][0] == 1 and scores[0][0] > 0.8


WIFI = {"title": "Wi-Fi not working", "description": "Wi-Fi is not working in B Block Hostel since yesterday evening.",
        "block": "B Block"}


def test_pipeline_links_duplicate_and_counts(student, other_student):
    first = submit_complaint(student, **WIFI).complaint
    second = submit_complaint(other_student, title="Wifi not working",
                              description="Wifi is not working in B block hostel since yesterday evening!", block="B Block")
    assert second.duplicate_of == first and second.similarity >= 0.85
    first.refresh_from_db()
    assert first.duplicate_count == 1
    assert DuplicateLink.objects.get().duplicate == second.complaint


def test_different_block_is_not_a_duplicate(student, other_student):
    submit_complaint(student, **WIFI)
    other = submit_complaint(other_student, **{**WIFI, "description": WIFI["description"].replace("B Block", "A Block"), "block": "A Block"})
    assert other.duplicate_of is None


def test_resolved_complaints_are_not_matched(student, other_student, admin_user):
    first = submit_complaint(student, **WIFI).complaint
    services.change_status(first, "resolved", admin_user)
    assert submit_complaint(other_student, **WIFI).duplicate_of is None


def test_duplicate_of_duplicate_links_to_original(student, other_student, db):
    from accounts.models import User

    third_student = User.objects.create_user("s3", "s3@college.edu", "Strong-Pass-123")
    first = submit_complaint(student, **WIFI).complaint
    submit_complaint(other_student, **WIFI)
    # Both earlier complaints match equally. If the search picks the duplicate,
    # the pipeline follows its link, so the new one is always attached to the original.
    third = submit_complaint(third_student, **WIFI)
    assert third.duplicate_of == first
    first.refresh_from_db()
    assert first.duplicate_count == 2


def test_threshold_is_configurable(student, other_student, monkeypatch):
    monkeypatch.setenv("DUPLICATE_THRESHOLD", "0.999")
    submit_complaint(student, **WIFI)
    second = submit_complaint(other_student, title="Wifi not working",
                              description="Wifi is not working in B block hostel since yesterday!", block="B Block")
    assert second.duplicate_of is None


def test_api_detail_shows_duplicate_of(api_as, student, other_student):
    first = submit_complaint(student, **WIFI).complaint
    response = api_as(other_student).post("/api/complaints/", WIFI, format="json")
    assert response.data["duplicate_of"]["id"] == first.id
