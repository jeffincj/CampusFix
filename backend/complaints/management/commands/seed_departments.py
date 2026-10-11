"""python manage.py seed_departments  -> re-create/refresh the 8 departments."""
from django.core.management.base import BaseCommand

from complaints.models import Department
from complaints.seed import DEPARTMENTS, seed_departments


class Command(BaseCommand):
    help = "Create or update the 8 campus departments."

    def handle(self, *args, **options):
        seed_departments(Department)
        self.stdout.write(self.style.SUCCESS(f"{len(DEPARTMENTS)} departments ready."))
