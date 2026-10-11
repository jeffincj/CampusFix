"""
Database tables for complaints:
departments, complaints, complaint_status_history, duplicate_links, feedback.
"""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Department(models.Model):
    """A campus department that fixes one kind of problem (e.g. Hostel, IT)."""

    code = models.CharField(max_length=20, unique=True)  # e.g. "HOSTEL"; also used as the complaint category
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)

    class Meta:
        db_table = "departments"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Complaint(models.Model):
    """One problem reported by a student."""

    # Category codes match Department.code, so category -> department is a direct lookup.
    class Category(models.TextChoices):
        HOSTEL = "HOSTEL", "Hostel"
        MESS = "MESS", "Mess & Food"
        IT = "IT", "Wi-Fi & IT"
        LAB = "LAB", "Labs & Academics"
        TRANSPORT = "TRANSPORT", "Transport"
        MAINTENANCE = "MAINTENANCE", "Electrical & Plumbing"
        SANITATION = "SANITATION", "Cleanliness & Sanitation"
        SECURITY = "SECURITY", "Safety & Security"

    class Urgency(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"
        REJECTED = "rejected", "Rejected"

    # Who reported it
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="complaints")

    # What the student wrote
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200, blank=True)  # free text, e.g. "Room 214, B Block"
    block = models.CharField(max_length=50, blank=True)  # building/block, used for per-block stats

    # Routing (filled by the student's hint now; by AI from Phase 5)
    category = models.CharField(max_length=20, choices=Category.choices, blank=True)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints"
    )
    urgency = models.CharField(max_length=10, choices=Urgency.choices, default=Urgency.MEDIUM)

    # AI fields (filled from Phase 5)
    summary = models.CharField(max_length=300, blank=True)
    language = models.CharField(max_length=20, blank=True)  # e.g. "en", "ta", "ml", "mixed"
    needs_review = models.BooleanField(default=False)  # True when LLM and classifier disagree
    duplicate_count = models.PositiveIntegerField(default=0)  # how many later complaints were merged into this one
    predicted_days = models.FloatField(null=True, blank=True)  # predicted resolution time
    llm_category = models.CharField(max_length=20, blank=True)  # what the LLM said
    ml_category = models.CharField(max_length=20, blank=True)  # what the classifier said
    ml_confidence = models.FloatField(null=True, blank=True)
    ai_source = models.CharField(max_length=20, blank=True)  # who decided the category: llm | classifier | student
    embedding = models.BinaryField(null=True, blank=True, editable=False)  # float32 vector for duplicate search
    embedding_model = models.CharField(max_length=80, blank=True)

    # Workflow
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "complaints"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["category"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"#{self.pk} {self.title}"

    @property
    def is_open(self):
        return self.status == self.Status.OPEN


class ComplaintStatusHistory(models.Model):
    """One row every time a complaint's status changes (an audit trail)."""

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="history")
    old_status = models.CharField(max_length=20, blank=True)  # blank for the first "created" entry
    new_status = models.CharField(max_length=20, choices=Complaint.Status.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "complaint_status_history"
        ordering = ["created_at", "id"]
        verbose_name_plural = "complaint status history"

    def __str__(self):
        return f"#{self.complaint_id}: {self.old_status or '-'} -> {self.new_status}"


class DuplicateLink(models.Model):
    """Links a new complaint to an older open complaint about the same problem (Phase 5)."""

    original = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="duplicates")
    duplicate = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="duplicate_of")
    similarity = models.FloatField()  # cosine similarity between the two complaints, 0..1
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "duplicate_links"
        constraints = [
            models.UniqueConstraint(fields=["original", "duplicate"], name="unique_duplicate_pair"),
        ]

    def __str__(self):
        return f"#{self.duplicate_id} duplicates #{self.original_id} ({self.similarity:.2f})"


class Feedback(models.Model):
    """A student's rating after their complaint is resolved (one per complaint)."""

    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, related_name="feedback")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "feedback"

    def __str__(self):
        return f"Feedback for #{self.complaint_id}: {self.rating}/5"
