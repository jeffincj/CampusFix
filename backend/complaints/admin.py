"""Django admin pages for complaints and related tables."""
from django import forms
from django.contrib import admin

from .models import Complaint, ComplaintStatusHistory, Department, DuplicateLink, Feedback
from .services import ALLOWED_TRANSITIONS


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "contact_email")
    search_fields = ("code", "name")


class StatusHistoryInline(admin.TabularInline):
    """Show the status timeline inside the complaint page (read-only)."""

    model = ComplaintStatusHistory
    extra = 0
    can_delete = False
    readonly_fields = ("old_status", "new_status", "changed_by", "note", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


class ComplaintAdminForm(forms.ModelForm):
    """Reject status changes that break the workflow rules."""

    class Meta:
        model = Complaint
        fields = "__all__"

    def clean_status(self):
        new = self.cleaned_data["status"]
        if self.instance.pk:
            old = self.instance.status
            if new != old and new not in ALLOWED_TRANSITIONS.get(old, []):
                raise forms.ValidationError(f"Cannot change status from '{old}' to '{new}'.")
        return new


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    form = ComplaintAdminForm
    list_display = ("id", "title", "category", "department", "urgency", "status", "needs_review", "duplicate_count", "created_at")
    list_filter = ("status", "category", "urgency", "needs_review", "department")
    search_fields = ("title", "description", "location", "student__username")
    readonly_fields = ("created_at", "updated_at", "resolved_at")
    inlines = [StatusHistoryInline]

    def save_model(self, request, obj, form, change):
        # Record a history row whenever an admin changes the status here.
        old_status = form.initial.get("status", "") if change else ""
        super().save_model(request, obj, form, change)
        if obj.status != old_status:
            ComplaintStatusHistory.objects.create(
                complaint=obj, old_status=old_status, new_status=obj.status,
                changed_by=request.user, note="Changed in Django admin",
            )


@admin.register(DuplicateLink)
class DuplicateLinkAdmin(admin.ModelAdmin):
    list_display = ("duplicate", "original", "similarity", "created_at")


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("complaint", "student", "rating", "created_at")
    list_filter = ("rating",)
