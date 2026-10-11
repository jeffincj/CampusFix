"""
python manage.py load_sample_data [--reset]

Loads data/sample_complaints.csv (SYNTHETIC) into the database so the
dashboard, hotspots and spikes have something to show.
- Dates are shifted so the newest synthetic complaint is "now".
- Synthetic students are created with unusable passwords (they cannot log in).
- Old complaints get a resolved/closed status using their resolution_days.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from ai.ml.common import SAMPLE_CSV, load_rows, parse_datetime
from complaints.models import Complaint, ComplaintStatusHistory
from complaints.services import department_for_category

SYNTHETIC_PREFIX = "synthetic_student_"


class Command(BaseCommand):
    help = "Load the synthetic sample complaints into the database."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete earlier synthetic data first.")
        parser.add_argument("--students", type=int, default=25)

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = User.objects.filter(username__startswith=SYNTHETIC_PREFIX).delete()
            self.stdout.write(f"Removed old synthetic data ({deleted} rows).")
        elif User.objects.filter(username__startswith=SYNTHETIC_PREFIX).exists():
            self.stdout.write(self.style.WARNING("Synthetic data already loaded. Use --reset to reload."))
            return

        students = [self.synthetic_student(i) for i in range(1, options["students"] + 1)]
        rows = load_rows([SAMPLE_CSV])
        newest = max(parse_datetime(r["created_at"]) for r in rows)
        now = timezone.now()
        # Move the newest complaint to "now". Shift by whole hours so hourly patterns (spikes) stay intact.
        shift = timedelta(hours=(timezone.make_naive(now) - newest) // timedelta(hours=1))

        for i, row in enumerate(rows):
            created_at = timezone.make_aware(parse_datetime(row["created_at"]) + shift)
            self.create_complaint(row, students[i % len(students)], created_at, now)

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(rows)} synthetic complaints for {len(students)} students."))

    def synthetic_student(self, number):
        user, created = User.objects.get_or_create(
            username=f"{SYNTHETIC_PREFIX}{number:02d}",
            defaults={"email": f"synthetic{number:02d}@example.invalid", "first_name": "Synthetic"},
        )
        if created:
            user.set_unusable_password()
            user.save()
        return user

    def create_complaint(self, row, student, created_at, now):
        resolve_at = created_at + timedelta(days=float(row["resolution_days"]))
        if resolve_at <= now:
            status = Complaint.Status.CLOSED if (now - resolve_at).days > 7 else Complaint.Status.RESOLVED
        elif now - created_at > timedelta(hours=12):
            status = Complaint.Status.IN_PROGRESS
        else:
            status = Complaint.Status.OPEN

        complaint = Complaint.objects.create(
            student=student, title=row["title"], description=row["description"], category=row["category"],
            department=department_for_category(row["category"]), urgency=row["urgency"], language=row["language"],
            location=row["location"], block=row["block"], status=status,
            resolved_at=resolve_at if status in ("resolved", "closed") else None,
        )
        # created_at uses auto_now_add, so set the historical date with an update.
        Complaint.objects.filter(pk=complaint.pk).update(created_at=created_at, updated_at=created_at)

        # Status history that matches the final status.
        steps = [("", "open", created_at)]
        if status != "open":
            steps.append(("open", "in_progress", created_at + timedelta(hours=2)))
        if status in ("resolved", "closed"):
            steps.append(("in_progress", "resolved", resolve_at))
        if status == "closed":
            steps.append(("resolved", "closed", resolve_at + timedelta(days=7)))
        for old, new, when in steps:
            entry = ComplaintStatusHistory.objects.create(
                complaint=complaint, old_status=old, new_status=new, note="Synthetic sample data"
            )
            ComplaintStatusHistory.objects.filter(pk=entry.pk).update(created_at=when)
        return complaint
