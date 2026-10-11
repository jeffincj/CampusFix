"""Phase 2 tests: departments, complaint CRUD, status workflow and history, role access."""
import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from accounts.models import User
from complaints import services
from complaints.models import Complaint, ComplaintStatusHistory, Department, Feedback

pytestmark = pytest.mark.django_db


# --- Seed data / models -------------------------------------------------------

def test_eight_departments_seeded():
    codes = set(Department.objects.values_list("code", flat=True))
    assert codes == set(Complaint.Category.values)  # one department per category
    assert len(codes) == 8


def test_staff_must_have_department():
    user = User(username="nodept", email="n@college.edu", role=User.Role.STAFF)
    with pytest.raises(ValidationError):
        user.clean()


def test_table_names():
    assert Complaint._meta.db_table == "complaints"
    assert ComplaintStatusHistory._meta.db_table == "complaint_status_history"
    assert Department._meta.db_table == "departments"
    assert Feedback._meta.db_table == "feedback"


# --- Creation -----------------------------------------------------------------

def test_create_complaint_routes_and_logs_history(complaint, hostel):
    assert complaint.department == hostel
    assert complaint.status == Complaint.Status.OPEN
    first = complaint.history.get()
    assert first.old_status == "" and first.new_status == "open"


def test_student_submits_complaint_via_form(client, student, it_dept):
    client.force_login(student)
    response = client.post(
        reverse("web:complaint_create"),
        {"title": "Wi-Fi down", "description": "ஹாஸ்டல் Wi-Fi not working since morning", "category": "IT",
         "location": "Library", "block": ""},
    )
    complaint = Complaint.objects.get()
    assert response.status_code == 302
    assert response.url == reverse("web:complaint_detail", args=[complaint.pk])
    assert complaint.student == student
    assert complaint.department == it_dept
    assert "ஹாஸ்டல்" in complaint.description  # Tamil text kept


def test_complaint_without_category_has_no_department(client, student):
    client.force_login(student)
    client.post(reverse("web:complaint_create"), {"title": "Problem", "description": "Something is broken here."})
    complaint = Complaint.objects.get()
    assert complaint.category == "" and complaint.department is None


def test_short_description_rejected(client, student):
    client.force_login(student)
    response = client.post(reverse("web:complaint_create"), {"title": "x", "description": "short"})
    assert response.status_code == 200
    assert Complaint.objects.count() == 0


def test_staff_cannot_submit_complaint(client, hostel_staff):
    client.force_login(hostel_staff)
    assert client.get(reverse("web:complaint_create")).status_code == 403


# --- Visibility by role -------------------------------------------------------

def test_visible_complaints_by_role(complaint, other_student, hostel_staff, it_staff, admin_user, student):
    assert list(services.visible_complaints(student)) == [complaint]
    assert list(services.visible_complaints(other_student)) == []
    assert list(services.visible_complaints(hostel_staff)) == [complaint]
    assert list(services.visible_complaints(it_staff)) == []
    assert list(services.visible_complaints(admin_user)) == [complaint]


def test_other_student_gets_404(client, complaint, other_student):
    client.force_login(other_student)
    assert client.get(reverse("web:complaint_detail", args=[complaint.pk])).status_code == 404


def test_list_page_filters(client, complaint, student):
    client.force_login(student)
    assert b"Fan not working" in client.get(reverse("web:complaint_list")).content
    assert b"Fan not working" not in client.get(reverse("web:complaint_list") + "?status=resolved").content
    assert b"Fan not working" not in client.get(reverse("web:complaint_list") + "?q=wifi").content
    assert b"Fan not working" in client.get(reverse("web:complaint_list") + "?q=fan").content


# --- Edit / delete ------------------------------------------------------------

def test_owner_edits_open_complaint(client, complaint, student, it_dept):
    client.force_login(student)
    client.post(
        reverse("web:complaint_edit", args=[complaint.pk]),
        {"title": "Wi-Fi in room", "description": "Actually it is the Wi-Fi router.", "category": "IT"},
    )
    complaint.refresh_from_db()
    assert complaint.title == "Wi-Fi in room"
    assert complaint.department == it_dept  # re-routed


def test_cannot_edit_after_work_started(client, complaint, student, hostel_staff):
    services.change_status(complaint, "in_progress", hostel_staff)
    client.force_login(student)
    assert client.get(reverse("web:complaint_edit", args=[complaint.pk])).status_code == 403
    assert client.post(reverse("web:complaint_delete", args=[complaint.pk])).status_code == 403


def test_owner_deletes_open_complaint(client, complaint, student):
    client.force_login(student)
    response = client.post(reverse("web:complaint_delete", args=[complaint.pk]))
    assert response.status_code == 302
    assert not Complaint.objects.exists()


# --- Status workflow ----------------------------------------------------------

def test_change_status_writes_history_and_resolved_at(complaint, hostel_staff):
    services.change_status(complaint, "in_progress", hostel_staff, "Electrician assigned")
    services.change_status(complaint, "resolved", hostel_staff)
    assert complaint.resolved_at is not None
    steps = list(complaint.history.values_list("old_status", "new_status"))
    assert steps == [("", "open"), ("open", "in_progress"), ("in_progress", "resolved")]


def test_invalid_transition_rejected(complaint, hostel_staff):
    with pytest.raises(services.StatusChangeError):
        services.change_status(complaint, "closed", hostel_staff)  # open -> closed not allowed
    complaint.refresh_from_db()
    assert complaint.status == "open"


def test_reopen_clears_resolved_at(complaint, hostel_staff):
    services.change_status(complaint, "resolved", hostel_staff)
    services.change_status(complaint, "in_progress", hostel_staff, "Still broken")
    assert complaint.resolved_at is None


def test_staff_updates_status_of_own_department(client, complaint, hostel_staff):
    client.force_login(hostel_staff)
    client.post(reverse("web:complaint_update_status", args=[complaint.pk]), {"status": "in_progress", "note": "On it"})
    complaint.refresh_from_db()
    assert complaint.status == "in_progress"
    assert complaint.history.last().changed_by == hostel_staff


def test_other_department_staff_cannot_update(client, complaint, it_staff):
    client.force_login(it_staff)
    response = client.post(reverse("web:complaint_update_status", args=[complaint.pk]), {"status": "in_progress"})
    assert response.status_code == 404  # cannot even see it
    complaint.refresh_from_db()
    assert complaint.status == "open"


def test_student_cannot_update_status(client, complaint, student):
    client.force_login(student)
    response = client.post(reverse("web:complaint_update_status", args=[complaint.pk]), {"status": "resolved"})
    assert response.status_code == 403


def test_admin_can_update_any(client, complaint, admin_user):
    client.force_login(admin_user)
    client.post(reverse("web:complaint_update_status", args=[complaint.pk]), {"status": "rejected"})
    complaint.refresh_from_db()
    assert complaint.status == "rejected"


# --- Feedback -----------------------------------------------------------------

def test_feedback_only_after_resolved_and_once(client, complaint, student, hostel_staff):
    client.force_login(student)
    url = reverse("web:complaint_feedback", args=[complaint.pk])
    assert client.post(url, {"rating": 5}).status_code == 403  # still open

    services.change_status(complaint, "resolved", hostel_staff)
    client.post(url, {"rating": 4, "comment": "Fixed quickly"})
    assert Feedback.objects.get().rating == 4
    assert client.post(url, {"rating": 1}).status_code == 403  # only once


# --- Live status JSON ---------------------------------------------------------

def test_status_json_only_returns_visible(client, complaint, student, other_student):
    url = reverse("web:complaint_status_json") + f"?ids={complaint.pk},999"
    client.force_login(student)
    data = client.get(url).json()
    assert data == {"complaints": [{"id": complaint.pk, "status": "open", "status_display": "Open",
                                    "updated_at": complaint.updated_at.isoformat()}]}
    client.force_login(other_student)
    assert client.get(url).json() == {"complaints": []}


# --- Django admin -------------------------------------------------------------

def test_admin_status_change_records_history(client, complaint):
    superuser = User.objects.create_superuser("root", "root@college.edu", "Strong-Pass-123")
    client.force_login(superuser)
    url = reverse("admin:complaints_complaint_change", args=[complaint.pk])
    form = client.get(url).context["adminform"].form
    data = {k: v for k, v in form.initial.items() if v is not None}
    data.update({
        "student": complaint.student_id, "department": complaint.department_id, "status": "in_progress",
        "duplicate_count": 0, "history-TOTAL_FORMS": 1, "history-INITIAL_FORMS": 1,
        "history-0-id": complaint.history.get().pk, "history-0-complaint": complaint.pk,
    })
    response = client.post(url, data)
    assert response.status_code == 302, response.context["adminform"].form.errors
    complaint.refresh_from_db()
    assert complaint.status == "in_progress"
    assert complaint.history.last().note == "Changed in Django admin"
