"""Shared helpers for the ML scripts: file paths, loading training data, features."""
import csv
import os
from datetime import datetime
from pathlib import Path

from django.conf import settings

# backend/data/
DATA_DIR = Path(settings.BASE_DIR) / "data"
SAMPLE_CSV = DATA_DIR / "sample_complaints.csv"
# Put real complaints (e.g. from the Google Form pilot) here with the same columns.
REAL_CSV = DATA_DIR / "real_complaints.csv"


def artifact_dir():
    """Folder where trained models are saved (set ML_ARTIFACT_DIR in .env to change)."""
    path = Path(os.getenv("ML_ARTIFACT_DIR", Path(settings.BASE_DIR) / "ai" / "ml" / "artifacts"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_csvs():
    """Synthetic data, plus real data if the file exists."""
    return [p for p in (SAMPLE_CSV, REAL_CSV) if p.exists()]


def load_rows(csv_paths=None):
    """Read complaint rows (dicts) from one or more CSV files."""
    rows = []
    for path in csv_paths or default_csvs():
        with open(path, newline="", encoding="utf-8") as f:
            rows.extend(csv.DictReader(f))
    return rows


def complaint_text(title, description):
    """The text the models read: title + description."""
    return f"{title or ''}. {description or ''}".strip(". ")


def time_features(category, urgency, block, created_at, text):
    """
    Features for the resolution-time model, as one dict.
    created_at is a datetime (aware or naive).
    """
    return {
        "category": category or "unknown",
        "urgency": urgency or "medium",
        "block": block or "unknown",
        "hour": created_at.hour,
        "weekday": created_at.weekday(),  # 0 = Monday
        "is_weekend": int(created_at.weekday() >= 5),
        "text_length": len(text or ""),
    }


def parse_datetime(value):
    return datetime.fromisoformat(value)
