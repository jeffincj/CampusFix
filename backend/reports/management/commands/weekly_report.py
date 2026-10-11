"""python manage.py weekly_report [--out file.pdf] [--end YYYY-MM-DD]  (e.g. from a weekly cron job)"""
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_date

from reports.weekly import build_weekly_pdf


class Command(BaseCommand):
    help = "Write the weekly PDF report to a file."

    def add_arguments(self, parser):
        parser.add_argument("--out", type=Path, default=None)
        parser.add_argument("--end", default="", help="Last day of the week (default: today)")

    def handle(self, *args, **options):
        end_day = parse_date(options["end"]) or timezone.localdate()
        out = options["out"] or Path(f"campusfix-weekly-{end_day}.pdf")
        out.write_bytes(build_weekly_pdf(end_day=end_day))
        self.stdout.write(self.style.SUCCESS(f"Report written to {out}"))
