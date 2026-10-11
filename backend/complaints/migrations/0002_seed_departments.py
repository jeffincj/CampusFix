"""Data migration: insert the 8 departments so every database starts with them."""
from django.db import migrations

from complaints.seed import seed_departments


def forwards(apps, schema_editor):
    # Use the historical model (apps.get_model), as Django recommends in migrations.
    seed_departments(apps.get_model("complaints", "Department"))


def backwards(apps, schema_editor):
    apps.get_model("complaints", "Department").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("complaints", "0001_initial")]
    operations = [migrations.RunPython(forwards, backwards)]
