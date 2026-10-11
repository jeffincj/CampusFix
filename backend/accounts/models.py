"""Custom user model with a role (student, staff, admin)."""
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    """
    Extends Django's built-in user (username, password, email, names)
    with a role. The role decides what each person can see and do.
    """

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        STAFF = "staff", "Staff"
        ADMIN = "admin", "Admin"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    email = models.EmailField(unique=True)  # one account per email
    # Staff belong to one department and only see its complaints.
    department = models.ForeignKey(
        "complaints.Department", on_delete=models.SET_NULL, null=True, blank=True, related_name="staff"
    )

    class Meta:
        db_table = "users"  # table name required by the project spec

    def clean(self):
        # Runs on admin/model-form validation: staff must have a department.
        super().clean()
        if self.role == self.Role.STAFF and not self.department_id:
            raise ValidationError({"department": "Staff users must belong to a department."})

    def save(self, *args, **kwargs):
        # A Django superuser (createsuperuser) is always an admin in our app.
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    # Small helpers so templates and views read clearly.
    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_staff_member(self):
        # Named "is_staff_member" because Django already uses "is_staff"
        # to mean "can log in to the Django admin site".
        return self.role == self.Role.STAFF

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    def __str__(self):
        return f"{self.username} ({self.role})"
