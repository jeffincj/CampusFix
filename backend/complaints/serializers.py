"""API serializers for complaints."""
from rest_framework import serializers

from .models import Complaint, ComplaintStatusHistory, Department


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "code", "name", "description"]


class StatusHistorySerializer(serializers.ModelSerializer):
    changed_by = serializers.CharField(source="changed_by.username", default=None)

    class Meta:
        model = ComplaintStatusHistory
        fields = ["old_status", "new_status", "changed_by", "note", "created_at"]


class ComplaintSerializer(serializers.ModelSerializer):
    """Read view used by the list endpoint."""

    student = serializers.CharField(source="student.username", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id", "title", "description", "category", "department", "department_name",
            "urgency", "location", "block", "summary", "language",
            "status", "status_display", "needs_review", "duplicate_count", "predicted_days",
            "llm_category", "ml_category", "ml_confidence", "ai_source",
            "student", "created_at", "updated_at", "resolved_at",
        ]
        read_only_fields = fields


class ComplaintDetailSerializer(ComplaintSerializer):
    """Detail view: everything above plus the status timeline."""

    history = StatusHistorySerializer(many=True, read_only=True)
    duplicate_of = serializers.SerializerMethodField()

    class Meta(ComplaintSerializer.Meta):
        fields = ComplaintSerializer.Meta.fields + ["history", "duplicate_of"]
        read_only_fields = fields

    def get_duplicate_of(self, complaint):
        """If this complaint was merged into an earlier one: {"id", "similarity"}."""
        link = complaint.duplicate_of.first()
        return {"id": link.original_id, "similarity": link.similarity} if link else None


class ComplaintCreateSerializer(serializers.ModelSerializer):
    """What a student sends to create a complaint."""

    class Meta:
        model = Complaint
        fields = ["title", "description", "category", "location", "block"]

    def validate_description(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("Please describe the problem in at least 10 characters.")
        return value


class ComplaintPatchSerializer(serializers.Serializer):
    """
    Fields that PATCH may change. Which of them a user may actually send
    depends on their role (see services.allowed_patch_fields).
    """

    title = serializers.CharField(max_length=200)
    description = serializers.CharField(min_length=10)
    location = serializers.CharField(max_length=200, allow_blank=True)
    block = serializers.CharField(max_length=50, allow_blank=True)
    category = serializers.ChoiceField(choices=Complaint.Category.choices, allow_blank=True)
    urgency = serializers.ChoiceField(choices=Complaint.Urgency.choices)
    needs_review = serializers.BooleanField()
    status = serializers.ChoiceField(choices=Complaint.Status.choices)
    note = serializers.CharField(max_length=300, allow_blank=True)  # goes into status history
