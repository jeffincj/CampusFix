"""
python manage.py ingest_documents [folder]

Loads every PDF in the folder (default: data/rules) into the RAG store.
A document with the same file name is replaced, so this is safe to run again.
"""
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from ai import rag
from ai.models import Document


class Command(BaseCommand):
    help = "Ingest rule PDFs for the chat assistant."

    def add_arguments(self, parser):
        parser.add_argument("folder", nargs="?", default=str(Path(settings.BASE_DIR) / "data" / "rules"))

    def handle(self, *args, **options):
        for path in sorted(Path(options["folder"]).glob("*.pdf")):
            for old in Document.objects.filter(file_name=path.name):
                old.file.delete(save=False)
                old.delete()
            with open(path, "rb") as f:
                document = Document.objects.create(title=path.stem.replace("_", " ").title(), file_name=path.name,
                                                   file=File(f, name=path.name))
            chunks = rag.ingest(document)
            self.stdout.write(f"{path.name}: {document.pages} pages, {chunks} chunks")
        self.stdout.write(self.style.SUCCESS("Documents ready."))
