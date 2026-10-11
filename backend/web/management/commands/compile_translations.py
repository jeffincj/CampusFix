"""
python manage.py compile_translations

Turns locale/<lang>/LC_MESSAGES/django.po (text, edited by people) into django.mo
(binary, read by Django). Same job as Django's "compilemessages", but written in pure
Python (polib), so it also works on Windows without installing GNU gettext.
"""
from pathlib import Path

import polib
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Compile the .po translation files into .mo files."

    def handle(self, *args, **options):
        for locale_dir in settings.LOCALE_PATHS:
            for po_path in sorted(Path(locale_dir).glob("*/LC_MESSAGES/django.po")):
                po = polib.pofile(str(po_path))
                po.save_as_mofile(str(po_path.with_suffix(".mo")))
                self.stdout.write(f"{po_path.parent.parent.name}: {po.percent_translated()}% translated")
        self.stdout.write(self.style.SUCCESS("Translations compiled."))
