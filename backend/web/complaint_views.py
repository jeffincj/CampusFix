"""HTML pages for complaints: submit, list, detail, edit, delete, status update, feedback."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from complaints import services
from complaints.forms import ComplaintForm, FeedbackForm, StatusUpdateForm
from complaints.models import Complaint


def get_visible_complaint(user, pk):
    """Fetch a complaint the user is allowed to see. Others' complaints give 404 (we don't reveal they exist)."""
    return get_object_or_404(services.visible_complaints(user), pk=pk)


@role_required("student")
def complaint_create(request):
    """Students submit a new complaint."""
    if request.method == "POST":
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = services.create_complaint(request.user, **form.cleaned_data)
            messages.success(request, f"Complaint #{complaint.pk} submitted. You can track it here.")
            return redirect("web:complaint_detail", pk=complaint.pk)
    else:
        form = ComplaintForm()
    return render(request, "web/complaint_form.html", {"form": form, "is_edit": False})


@login_required
def complaint_list(request):
    """
    One list page for every role. What it shows comes from visible_complaints():
    students see their own, staff their department's, admins everything.
    """
    complaints = services.visible_complaints(request.user)

    # Simple filters from the query string: ?status=open&q=wifi
    status = request.GET.get("status", "")
    query = request.GET.get("q", "").strip()
    if status in Complaint.Status.values:
        complaints = complaints.filter(status=status)
    if query:
        complaints = complaints.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(location__icontains=query))

    page = Paginator(complaints, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "web/complaint_list.html",
        {"page": page, "status": status, "query": query, "statuses": Complaint.Status.choices},
    )


@login_required
def complaint_detail(request, pk):
    """Show one complaint with its status timeline and the actions this user may take."""
    complaint = get_visible_complaint(request.user, pk)
    user = request.user
    context = {
        "complaint": complaint,
        "history": complaint.history.select_related("changed_by"),
        "can_edit": services.can_edit(user, complaint),
        # Show the status form only if the user may update AND there is somewhere to move to.
        "can_update_status": services.can_update_status(user, complaint) and bool(services.ALLOWED_TRANSITIONS[complaint.status]),
        "can_give_feedback": services.can_give_feedback(user, complaint),
        "feedback": getattr(complaint, "feedback", None),
    }
    if context["can_update_status"]:
        context["status_form"] = StatusUpdateForm(complaint=complaint)
    if context["can_give_feedback"]:
        context["feedback_form"] = FeedbackForm()
    return render(request, "web/complaint_detail.html", context)


@role_required("student")
def complaint_edit(request, pk):
    """Students can fix their own complaint while it is still open."""
    complaint = get_visible_complaint(request.user, pk)
    if not services.can_edit(request.user, complaint):
        raise PermissionDenied("Only open complaints can be edited.")

    if request.method == "POST":
        form = ComplaintForm(request.POST, instance=complaint)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.department = services.department_for_category(complaint.category)  # re-route if category changed
            complaint.save()
            messages.success(request, "Complaint updated.")
            return redirect("web:complaint_detail", pk=complaint.pk)
    else:
        form = ComplaintForm(instance=complaint)
    return render(request, "web/complaint_form.html", {"form": form, "is_edit": True, "complaint": complaint})


@role_required("student")
def complaint_delete(request, pk):
    """Students can withdraw their own open complaint. GET asks to confirm, POST deletes."""
    complaint = get_visible_complaint(request.user, pk)
    if not services.can_edit(request.user, complaint):
        raise PermissionDenied("Only open complaints can be deleted.")

    if request.method == "POST":
        complaint.delete()
        messages.success(request, "Complaint deleted.")
        return redirect("web:complaint_list")
    return render(request, "web/complaint_confirm_delete.html", {"complaint": complaint})


@require_POST
@role_required("staff", "admin")
def complaint_update_status(request, pk):
    """Staff (own department) and admins change the status."""
    complaint = get_visible_complaint(request.user, pk)
    if not services.can_update_status(request.user, complaint):
        raise PermissionDenied("You cannot update this complaint.")

    form = StatusUpdateForm(request.POST, complaint=complaint)
    if form.is_valid():
        services.change_status(complaint, form.cleaned_data["status"], request.user, form.cleaned_data["note"])
        messages.success(request, f"Status changed to {complaint.get_status_display()}.")
    else:
        messages.error(request, "That status change is not allowed.")
    return redirect("web:complaint_detail", pk=pk)


@require_POST
@role_required("student")
def complaint_feedback(request, pk):
    """The owner rates a resolved complaint once."""
    complaint = get_visible_complaint(request.user, pk)
    if not services.can_give_feedback(request.user, complaint):
        raise PermissionDenied("Feedback is not possible for this complaint.")

    form = FeedbackForm(request.POST)
    if form.is_valid():
        feedback = form.save(commit=False)
        feedback.complaint = complaint
        feedback.student = request.user
        feedback.save()
        messages.success(request, "Thank you for your feedback!")
    else:
        messages.error(request, "Please choose a rating from 1 to 5.")
    return redirect("web:complaint_detail", pk=pk)


@login_required
def complaint_status_json(request):
    """
    Small JSON endpoint for live status refresh (used by status.js).
    GET /complaints/status.json?ids=3,7,9  ->  {"complaints": [{"id": 3, "status": "open", ...}]}
    Only returns complaints the user is allowed to see.
    """
    ids = [int(i) for i in request.GET.get("ids", "").split(",") if i.strip().isdigit()][:100]
    rows = services.visible_complaints(request.user).filter(pk__in=ids)
    data = [
        {
            "id": c.pk,
            "status": c.status,
            "status_display": c.get_status_display(),
            "updated_at": c.updated_at.isoformat(),
        }
        for c in rows
    ]
    return JsonResponse({"complaints": data})
