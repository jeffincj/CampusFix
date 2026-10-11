"""
Business rules for complaints, kept in one place so the HTML pages,
the Django admin, and the REST API (Phase 3) all behave the same way.
"""
from django.db import transaction
from django.utils import timezone

from .models import Complaint, ComplaintStatusHistory, Department

Status = Complaint.Status

# Which status can move to which. Anything not listed is not allowed.
ALLOWED_TRANSITIONS = {
    Status.OPEN: [Status.IN_PROGRESS, Status.RESOLVED, Status.REJECTED],
    Status.IN_PROGRESS: [Status.RESOLVED, Status.OPEN],
    Status.RESOLVED: [Status.CLOSED, Status.IN_PROGRESS],  # reopen if the fix did not work
    Status.CLOSED: [],
    Status.REJECTED: [],
}


class StatusChangeError(Exception):
    """Raised when a status change is not allowed."""


# --- Who can see / change what -------------------------------------------------

def visible_complaints(user):
    """
    The single rule for "which complaints can this user see":
    student -> own, staff -> own department, admin -> all.
    """
    qs = Complaint.objects.select_related("student", "department")
    if user.is_admin:
        return qs
    if user.is_staff_member:
        if user.department_id is None:
            return qs.none()
        return qs.filter(department_id=user.department_id)
    return qs.filter(student=user)


def can_update_status(user, complaint):
    """Only admins, or staff of the complaint's department, can change status."""
    if user.is_admin:
        return True
    return user.is_staff_member and user.department_id is not None and user.department_id == complaint.department_id


def can_edit(user, complaint):
    """A student can edit or delete their own complaint only while it is still open."""
    return complaint.student_id == user.id and complaint.is_open


def can_give_feedback(user, complaint):
    """The owner can rate a complaint once, after it is resolved or closed."""
    return (
        complaint.student_id == user.id
        and complaint.status in (Status.RESOLVED, Status.CLOSED)
        and not hasattr(complaint, "feedback")
    )


# --- Actions -------------------------------------------------------------------

def department_for_category(category):
    """Find the department whose code matches the category (or None)."""
    if not category:
        return None
    return Department.objects.filter(code=category).first()


@transaction.atomic
def create_complaint(student, **fields):
    """
    Create a complaint, route it to a department, and write the first
    history row. Phase 5 will add the AI pipeline here.
    """
    complaint = Complaint(student=student, **fields)
    complaint.department = department_for_category(complaint.category)
    complaint.save()
    ComplaintStatusHistory.objects.create(
        complaint=complaint, old_status="", new_status=complaint.status, changed_by=student, note="Complaint submitted"
    )
    return complaint


@transaction.atomic
def change_status(complaint, new_status, user, note=""):
    """
    Move a complaint to a new status if the rules allow it,
    and record the change in complaint_status_history.
    """
    old_status = complaint.status
    if new_status not in ALLOWED_TRANSITIONS.get(old_status, []):
        raise StatusChangeError(f"Cannot change status from '{old_status}' to '{new_status}'.")

    complaint.status = new_status
    if new_status == Status.RESOLVED:
        complaint.resolved_at = timezone.now()
    elif new_status in (Status.OPEN, Status.IN_PROGRESS):
        complaint.resolved_at = None  # reopened
    complaint.save(update_fields=["status", "resolved_at", "updated_at"])

    ComplaintStatusHistory.objects.create(
        complaint=complaint, old_status=old_status, new_status=new_status, changed_by=user, note=note
    )
    return complaint
