"""
Resolution-time model: Random Forest regression -> predicted days to resolve.

Features (see common.time_features): category, urgency, block, hour of day,
weekday, weekend flag, text length. DictVectorizer turns the text columns
into one-hot columns, so no pandas is needed.
"""
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_extraction import DictVectorizer
from sklearn.pipeline import Pipeline

from .common import artifact_dir, complaint_text, load_rows, parse_datetime, time_features

MODEL_FILE = "time_model.joblib"
_cache = {}


def build_pipeline():
    return Pipeline([
        ("vectorize", DictVectorizer(sparse=False)),
        ("forest", RandomForestRegressor(n_estimators=200, min_samples_leaf=2, random_state=42)),
    ])


def features_and_targets(rows):
    features, targets = [], []
    for r in rows:
        text = complaint_text(r["title"], r["description"])
        features.append(time_features(r["category"], r["urgency"], r["block"], parse_datetime(r["created_at"]), text))
        targets.append(float(r["resolution_days"]))
    return features, targets


def train(rows):
    features, targets = features_and_targets(rows)
    return build_pipeline().fit(features, targets)


def model_path():
    return artifact_dir() / MODEL_FILE


def save(model, path=None):
    path = path or model_path()
    joblib.dump(model, path)
    return path


def load_model(path=None):
    path = path or model_path()
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    if path not in _cache or _cache[path][0] != mtime:
        _cache[path] = (mtime, joblib.load(path))
    return _cache[path][1]


def predict_days(category, urgency, block, created_at, text, model=None):
    """Predicted days to resolve (rounded to 0.1), or None if no model is trained."""
    model = model or load_model()
    if model is None:
        return None
    features = time_features(category, urgency, block, created_at, text)
    return round(float(model.predict([features])[0]), 1)


def main(csv_paths=None):
    rows = load_rows(csv_paths)
    model = train(rows)
    path = save(model)
    print(f"Time model trained on {len(rows)} complaints -> {path}")
    return model
