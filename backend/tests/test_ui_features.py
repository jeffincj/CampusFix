"""Tests for the redesigned student site: live AI preview, campus pulse, progress tracker."""
import pytest
from django.urls import reverse

from complaints import services
from web.complaint_views import progress_steps

pytestmark = pytest.mark.django_db

PREVIEW = reverse("web:complaint_preview")


# --- Live AI preview ----------------------------------------------------------

def test_preview_with_classifier(client, student, saved_classifier):
    client.force_login(student)
    data = client.post(PREVIEW, {"title": "Wifi illa", "description": "B Block Hostel la wifi work aagala since evening",
                                 "location": ""}).json()
    assert data["ready"] and data["allowed"]
    assert data["category"] == "Wi-Fi & IT"
    assert data["department"] == "IT Services"
    assert 0 < data["confidence"] <= 100
    assert data["language"] == "Mixed language"
    assert data["location"] == "B Block Hostel"
    assert data["urgency"] == "high"  # "work aagala"/"not working" style problem


def test_preview_needs_some_text(client, student):
    client.force_login(student)
    assert client.post(PREVIEW, {"title": "", "description": "hi"}).json() == {"ready": False}


def test_preview_warns_about_spam(client, student):
    client.force_login(student)
    data = client.post(PREVIEW, {"title": "Offer", "description": "cheap phones at http://spam.example"}).json()
    assert data["allowed"] is False
    assert "Links are not allowed" in data["warning"]


def test_preview_finds_similar_open_complaint(client, student, other_student):
    from ai.pipeline import submit_complaint

    text = {"title": "Wi-Fi not working", "description": "Wi-Fi is not working in B Block Hostel since evening.", "block": "B Block"}
    submit_complaint(other_student, **text)
    client.force_login(student)
    data = client.post(PREVIEW, {"title": text["title"], "description": text["description"]}).json()
    assert data["similar_reported"] is True


def test_preview_saves_nothing_and_is_student_only(client, student, hostel_staff):
    from complaints.models import Complaint

    client.force_login(student)
    client.post(PREVIEW, {"title": "Fan broken", "description": "The fan in my hostel room is broken"})
    assert Complaint.objects.count() == 0
    client.force_login(hostel_staff)
    assert client.post(PREVIEW, {"title": "x", "description": "Fan broken in room"}).status_code == 403
    client.force_login(student)
    assert client.get(PREVIEW).status_code == 405  # POST only


def test_new_complaint_page_has_preview_and_mic(client, student):
    client.force_login(student)
    page = client.get(reverse("web:complaint_create")).content.decode()
    assert "Live AI preview" in page and "data-preview-url" in page
    assert "data-mic" in page and 'data-lang="en"' in page


# --- Home page campus pulse --------------------------------------------------------

def test_home_shows_campus_pulse(client, student, hostel_staff):
    first = services.create_complaint(student, title="Fan", description="Fan broken in room", category="HOSTEL")
    services.create_complaint(student, title="Fan 2", description="Another fan broken", category="HOSTEL")
    services.change_status(first, "resolved", hostel_staff)
    page = client.get(reverse("web:home")).content.decode()
    assert "Campus pulse" in page
    assert "50%" in page  # 1 of 2 resolved
    assert "Hostel" in page  # most reported this week


def test_home_pulse_with_no_data(client):
    response = client.get(reverse("web:home"))
    assert response.status_code == 200
    assert response.context["pulse"]["resolved_percent"] == 0


# --- Progress tracker ---------------------------------------------------------------

def test_progress_steps(complaint, hostel_staff):
    assert [s["state"] for s in progress_steps(complaint)] == ["current", "todo", "todo", "todo"]
    services.change_status(complaint, "in_progress", hostel_staff)
    services.change_status(complaint, "resolved", hostel_staff)
    assert [s["state"] for s in progress_steps(complaint)] == ["done", "done", "current", "todo"]


def test_progress_steps_rejected(complaint, admin_user):
    services.change_status(complaint, "rejected", admin_user)
    assert [s["state"] for s in progress_steps(complaint)] == ["done", "rejected"]


def test_detail_page_shows_stepper_and_theme_toggle(client, complaint, student):
    client.force_login(student)
    page = client.get(reverse("web:complaint_detail", args=[complaint.pk])).content.decode()
    assert 'class="stepper"' in page
    assert "data-theme-toggle" in page
