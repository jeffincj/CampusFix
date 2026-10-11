"""
python manage.py train_models [--csv path ...] [--skip-eval]

1. Evaluates the classifier and time model on a held-out 20% (saved to model_metrics).
2. Trains the final models on ALL rows and saves them to ML_ARTIFACT_DIR.
Uses data/sample_complaints.csv, plus data/real_complaints.csv if it exists.
"""
from pathlib import Path

from django.core.management.base import BaseCommand

from ai.ml import evaluate, train_classifier, train_time_model


class Command(BaseCommand):
    help = "Evaluate and train the ML models."

    def add_arguments(self, parser):
        parser.add_argument("--csv", nargs="*", type=Path, help="Training CSV files (default: data/*.csv)")
        parser.add_argument("--skip-eval", action="store_true", help="Only train, don't evaluate.")

    def handle(self, *args, **options):
        csvs = options["csv"] or None
        if not options["skip_eval"]:
            evaluate.main(csvs)
        train_classifier.main(csvs)
        train_time_model.main(csvs)
        self.stdout.write(self.style.SUCCESS("Models ready."))
