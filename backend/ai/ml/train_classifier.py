"""
Department classifier: TF-IDF features + Logistic Regression.

    python manage.py train_models          (trains and evaluates all models)

Why these features:
- character n-grams (2-5 letters) work for any script, including Tamil,
  Malayalam and mixed "Tanglish/Manglish", and survive spelling variations
  ("wifi", "wi-fi", "வைஃபை").
- word n-grams add whole-word clues ("bus", "mess", "projector").
"""
from dataclasses import dataclass

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline

from .common import artifact_dir, complaint_text, load_rows

MODEL_FILE = "classifier.joblib"

# Words are runs of non-space, non-punctuation characters. (The default \w+ pattern
# would cut Tamil/Malayalam words at their vowel signs.)
WORD_PATTERN = r"[^\s.,!?;:()\"'\-/]+"

_cache = {}  # path -> (modified time, model) so we load the file only once


@dataclass
class Prediction:
    label: str  # department code, e.g. "IT"
    confidence: float  # probability of that label, 0..1
    probabilities: dict  # every label -> probability


def build_pipeline():
    features = FeatureUnion([
        ("chars", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, lowercase=True)),
        ("words", TfidfVectorizer(analyzer="word", token_pattern=WORD_PATTERN, ngram_range=(1, 2), sublinear_tf=True)),
    ])
    classifier = LogisticRegression(max_iter=3000, C=5.0, class_weight="balanced")
    return Pipeline([("features", features), ("classifier", classifier)])


def texts_and_labels(rows):
    texts = [complaint_text(r["title"], r["description"]) for r in rows]
    labels = [r["category"] for r in rows]
    return texts, labels


def train(rows):
    """Fit a new pipeline on the given rows and return it."""
    texts, labels = texts_and_labels(rows)
    return build_pipeline().fit(texts, labels)


def model_path():
    return artifact_dir() / MODEL_FILE


def save(model, path=None):
    path = path or model_path()
    joblib.dump(model, path)
    return path


def load_model(path=None):
    """Load the saved model (cached). Returns None if it has not been trained yet."""
    path = path or model_path()
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    if path not in _cache or _cache[path][0] != mtime:
        _cache[path] = (mtime, joblib.load(path))
    return _cache[path][1]


def predict(text, model=None):
    """Predict the department for one complaint text. None if no model is available."""
    model = model or load_model()
    if model is None:
        return None
    probs = model.predict_proba([text])[0]
    by_label = {label: float(p) for label, p in zip(model.classes_, probs)}
    best = max(by_label, key=by_label.get)
    return Prediction(label=best, confidence=by_label[best], probabilities=by_label)


def main(csv_paths=None):
    rows = load_rows(csv_paths)
    model = train(rows)
    path = save(model)
    print(f"Classifier trained on {len(rows)} complaints -> {path}")
    return model

