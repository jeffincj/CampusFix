"""
python manage.py train_models [--csv path ...] [--skip-eval]

1. Evaluates the classifier and time model on a held-out 20% (saved to model_metrics).
2. Trains the final models on ALL rows and saves them to ML_ARTIFACT_DIR.
Uses data/sample_complaints.csv, plus data/real_complaints.csv if it exists.
--llm-sample N also measures the LLM's accuracy on N test rows (needs an API key).
"""
from pathlib import Path

from django.core.management.base import BaseCommand

from ai.ml import evaluate, train_classifier, train_time_model
from ai.models import ModelMetric


class Command(BaseCommand):
    help = "Evaluate and train the ML models."

    def add_arguments(self, parser):
        parser.add_argument("--csv", nargs="*", type=Path, help="Training CSV files (default: data/*.csv)")
        parser.add_argument("--skip-eval", action="store_true", help="Only train, don't evaluate.")
        parser.add_argument("--if-needed", action="store_true",
                            help="Only train if no model file exists, only evaluate if no metrics are saved (for start-up).")
        parser.add_argument("--llm-sample", type=int, default=0,
                            help="Also evaluate the LLM on N test rows (uses the API, costs money).")

    def handle(self, *args, **options):
        csvs = options["csv"] or None
        if options["if_needed"]:
            if not ModelMetric.objects.filter(model_name="classifier").exists():
                evaluate.main(csvs)
            if not train_classifier.model_path().exists():
                train_classifier.main(csvs)
            if not train_time_model.model_path().exists():
                train_time_model.main(csvs)
            self.stdout.write(self.style.SUCCESS("Models ready."))
            return
        if not options["skip_eval"]:
            evaluate.main(csvs, llm_sample=options["llm_sample"])
        train_classifier.main(csvs)
        train_time_model.main(csvs)
        self.stdout.write(self.style.SUCCESS("Models ready."))
