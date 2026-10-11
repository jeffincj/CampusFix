"""Phase 3 tests: complaints API with role-based access."""
from datetime import timedelta

import pytest
from django.utils import timezone

from complaints import services
from complaints.models import Complaint

pytestmark = pytest.mark.django_db

NEW = {"title": "Wi-Fi down", "description": "Wi-Fi not working in the library since morning", "category": "IT", "location": "Library"}


# --- Create -------------------------------------------------------------------

def test_student_creates_complaint(api_as, student, it_dept):
    response = api_as(student).post("/api/complaints/", NEW, format="json")
    assert response.status_code == 201
    assert response.data["department"] == it_dept.id
    assert response.data["student"] == student.username
    assert response.data["history"][0]["new_status"] == "open"


def test_create_ignores_readonly_fields(api_as, student):
    data = {**NEW, "status": "resolved", "needs_review": True, "student": 999}
    response = api_as(student).post("/api/complaints/", data, format="json")
    complaint = Complaint.objects.get(pk=response.data["id"])
    assert complaint.status == "open" and not complaint.needs_review and complaint.student == student


def test_create_validation(api_as, student):
    response = api_as(student).post("/api/complaints/", {"title": "", "description": "short"}, format="json")
    assert response.status_code == 400
    assert {"title", "description"} <= set(response.data)


@pytest.mark.parametrize("who", ["hostel_staff", "admin_user"])
def test_only_students_create(api_as, request, who):
    user = request.getfixturevalue(who)
    assert api_as(user).post("/api/complaints/", NEW, format="json").status_code == 403


# --- List / detail visibility -------------------------------------------------

def test_list_visibility_by_role(api_as, complaint, student, other_student, hostel_staff, it_staff, admin_user):
    def ids(user):
        return [c["id"] for c in api_as(user).get("/api/complaints/").data["results"]]

    assert ids(student) == [complaint.id]
    assert ids(other_student) == []
    assert ids(hostel_staff) == [complaint.id]
    assert ids(it_staff) == []
    assert ids(admin_user) == [complaint.id]


def test_detail_hidden_from_others(api_as, complaint, other_student, it_staff):
    assert api_as(other_student).get(f"/api/complaints/{complaint.id}/").status_code == 404
    assert api_as(it_staff).get(f"/api/complaints/{complaint.id}/").status_code == 404


def test_detail_has_history(api_as, complaint, student):
    response = api_as(student).get(f"/api/complaints/{complaint.id}/")
    assert response.status_code == 200
    assert response.data["history"][0]["note"] == "Complaint submitted"


def test_list_filters_and_search(api_as, student, admin_user):
    services.create_complaint(student, title="Fan broken", description="Ceiling fan broken in room", category="HOSTEL", block="A")
    services.create_complaint(student, title="Bus late", description="College bus is always late", category="TRANSPORT", urgency="high")
    client = api_as(admin_user)

    def titles(query):
        return [c["title"] for c in client.get(f"/api/complaints/?{query}").data["results"]]

    assert titles("category=TRANSPORT") == ["Bus late"]
    assert titles("urgency=high") == ["Bus late"]
    assert titles("block=A") == ["Fan broken"]
    assert titles("q=fan") == ["Fan broken"]
    assert titles("status=resolved") == []
    assert titles("ordering=title") == ["Bus late", "Fan broken"]  # not an allowed field -> ignored, newest first
    assert titles("ordering=created_at") == ["Fan broken", "Bus late"]


def test_list_date_filter(api_as, complaint, admin_user):
    today = timezone.localdate()
    client = api_as(admin_user)
    assert client.get(f"/api/complaints/?from={today}&to={today}").data["count"] == 1
    assert client.get(f"/api/complaints/?from={today + timedelta(days=1)}").data["count"] == 0


def test_list_is_paginated(api_as, student, admin_user):
    for i in range(25):
        services.create_complaint(student, title=f"C{i}", description="Some problem description")
    data = api_as(admin_user).get("/api/complaints/").data
    assert data["count"] == 25 and len(data["results"]) == 20 and data["next"]


# --- PATCH by role ------------------------------------------------------------

def test_staff_changes_status_with_note(api_as, complaint, hostel_staff):
    response = api_as(hostel_staff).patch(
        f"/api/complaints/{complaint.id}/", {"status": "in_progress", "note": "Electrician assigned", "urgency": "high"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["status"] == "in_progress" and response.data["urgency"] == "high"
    last = response.data["history"][-1]
    assert last["note"] == "Electrician assigned" and last["changed_by"] == "warden"


def test_staff_cannot_edit_text_fields(api_as, complaint, hostel_staff):
    response = api_as(hostel_staff).patch(f"/api/complaints/{complaint.id}/", {"title": "hacked"}, format="json")
    assert response.status_code == 403
    assert "title" in str(response.data)


def test_invalid_transition_is_400_and_rolls_back(api_as, complaint, hostel_staff):
    response = api_as(hostel_staff).patch(
        f"/api/complaints/{complaint.id}/", {"status": "closed", "urgency": "critical"}, format="json"
    )
    assert response.status_code == 400
    complaint.refresh_from_db()
    assert complaint.status == "open" and complaint.urgency == "medium"  # urgency change undone too


def test_other_department_staff_gets_404(api_as, complaint, it_staff):
    assert api_as(it_staff).patch(f"/api/complaints/{complaint.id}/", {"status": "in_progress"}, format="json").status_code == 404


def test_student_edits_own_open_complaint(api_as, complaint, student, it_dept):
    response = api_as(student).patch(f"/api/complaints/{complaint.id}/", {"category": "IT"}, format="json")
    assert response.status_code == 200
    assert response.data["department"] == it_dept.id  # re-routed


def test_student_cannot_change_status(api_as, complaint, student):
    response = api_as(student).patch(f"/api/complaints/{complaint.id}/", {"status": "resolved"}, format="json")
    assert response.status_code == 403


def test_student_cannot_edit_after_work_started(api_as, complaint, student, hostel_staff):
    services.change_status(complaint, "in_progress", hostel_staff)
    response = api_as(student).patch(f"/api/complaints/{complaint.id}/", {"title": "new"}, format="json")
    assert response.status_code == 403


def test_admin_reroutes_and_clears_review_flag(api_as, complaint, admin_user, it_dept):
    complaint.needs_review = True
    complaint.save()
    response = api_as(admin_user).patch(
        f"/api/complaints/{complaint.id}/", {"category": "IT", "needs_review": False}, format="json"
    )
    assert response.status_code == 200
    assert response.data["department"] == it_dept.id and response.data["needs_review"] is False


def test_bad_values_rejected(api_as, complaint, admin_user):
    response = api_as(admin_user).patch(f"/api/complaints/{complaint.id}/", {"urgency": "extreme"}, format="json")
    assert response.status_code == 400


def test_put_and_delete_not_allowed(api_as, complaint, admin_user):
    client = api_as(admin_user)
    assert client.put(f"/api/complaints/{complaint.id}/", NEW, format="json").status_code == 405
    assert client.delete(f"/api/complaints/{complaint.id}/").status_code == 405


# --- Stats --------------------------------------------------------------------

def test_stats_for_admin(api_as, student, admin_user):
    services.create_complaint(student, title="A", description="Fan broken in room", category="HOSTEL", block="A")
    services.create_complaint(student, title="B", description="Another fan broken", category="HOSTEL", block="A")
    services.create_complaint(student, title="C", description="Bus late every day", category="TRANSPORT", block="B")
    data = api_as(admin_user).get("/api/complaints/stats/").data
    assert data["total"] == 3
    assert data["by_category"][0] == {"key": "HOSTEL", "count": 2}
    assert {"key": "B", "count": 1} in data["by_block"]
    assert len(data["by_week"]) == 12
    assert data["by_week"][-1]["count"] == 3  # all created this week


def test_stats_for_staff_only_own_department(api_as, complaint, student, it_staff):
    services.create_complaint(student, title="Wifi", description="Wifi not working at all", category="IT")
    data = api_as(it_staff).get("/api/complaints/stats/?weeks=4").data
    assert data["total"] == 1 and len(data["by_week"]) == 4


def test_stats_forbidden_for_students(api_as, student):
    assert api_as(student).get("/api/complaints/stats/").status_code == 403


def test_departments_list(api_as, student):
    data = api_as(student).get("/api/departments/").data
    assert len(data) == 8
