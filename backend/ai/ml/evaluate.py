"""
Evaluate the models on data they have NOT seen (80/20 split) and save
the results in the model_metrics table.

Classifier: accuracy, precision, recall, F1 (macro = average over
departments, so small departments count as much as big ones), confusion matrix.
Time model: MAE (average error in days) and R².
"""
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    mean_absolute_error,
    precision_recall_fscore_support,
    r2_score,
)
from sklearn.model_selection import train_test_split

from ai.models import ModelMetric

from . import train_classifier, train_time_model
from .common import load_rows

TEST_SIZE = 0.2
SEED = 42


def classification_metrics(true_labels, predicted_labels, labels):
    """All classification numbers in one dict (also used for the LLM evaluation)."""
    precision, recall, f1, _ = precision_recall_fscore_support(
        true_labels, predicted_labels, labels=labels, average="macro", zero_division=0
    )
    per_class = precision_recall_fscore_support(true_labels, predicted_labels, labels=labels, zero_division=0)
    return {
        "accuracy": round(accuracy_score(true_labels, predicted_labels), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "labels": labels,
        # rows = true label, columns = predicted label
        "confusion_matrix": confusion_matrix(true_labels, predicted_labels, labels=labels).tolist(),
        "per_class": {
            label: {"precision": round(float(p), 4), "recall": round(float(r), 4), "support": int(s)}
            for label, p, r, s in zip(labels, per_class[0], per_class[1], per_class[3])
        },
    }


def split(rows):
    labels = [r["category"] for r in rows]
    return train_test_split(rows, test_size=TEST_SIZE, random_state=SEED, stratify=labels)


def evaluate_classifier(rows, save=True):
    train_rows, test_rows = split(rows)
    model = train_classifier.train(train_rows)
    texts, true_labels = train_classifier.texts_and_labels(test_rows)
    predicted = list(model.predict(texts))
    metrics = classification_metrics(true_labels, predicted, sorted(set(r["category"] for r in rows)))
    if save:
        ModelMetric.objects.create(model_name="classifier", metrics=metrics, n_train=len(train_rows), n_test=len(test_rows))
    return metrics


def evaluate_time_model(rows, save=True):
    train_rows, test_rows = split(rows)
    model = train_time_model.train(train_rows)
    features, targets = train_time_model.features_and_targets(test_rows)
    predicted = model.predict(features)
    # Baseline: always predict the average. A useful model must beat this.
    average = sum(float(r["resolution_days"]) for r in train_rows) / len(train_rows)
    metrics = {
        "mae_days": round(float(mean_absolute_error(targets, predicted)), 3),
        "r2": round(float(r2_score(targets, predicted)), 4),
        "baseline_mae_days": round(float(mean_absolute_error(targets, [average] * len(targets))), 3),
    }
    if save:
        ModelMetric.objects.create(model_name="time_model", metrics=metrics, n_train=len(train_rows), n_test=len(test_rows))
    return metrics


def evaluate_llm(rows, sample_size=40, client=None, save=True):
    """
    Run the LLM intake on a sample of the SAME test split as the classifier, so the two
    accuracies can be compared fairly. Costs API calls, so it is opt-in (--llm-sample).
    """
    import time

    from ai import intake

    _, test_rows = split(rows)
    sample = test_rows[:sample_size]
    true_labels, predicted, latencies, failures = [], [], [], 0
    for row in sample:
        started = time.monotonic()
        try:
            result = intake.extract(f"{row['title']}. {row['description']}", client=client)
            predicted.append(result["category"])
        except intake.IntakeError:
            failures += 1
            predicted.append("FAILED")
        latencies.append((time.monotonic() - started) * 1000)
        true_labels.append(row["category"])
    metrics = classification_metrics(true_labels, predicted, sorted(set(r["category"] for r in rows)))
    metrics.update({"failures": failures, "avg_latency_ms": round(sum(latencies) / len(latencies))})
    if save:
        ModelMetric.objects.create(model_name="llm_intake", metrics=metrics, n_test=len(sample),
                                   notes=f"sample of {len(sample)} test rows")
    return metrics


def main(csv_paths=None, llm_sample=0):
    rows = load_rows(csv_paths)
    results = {"classifier": evaluate_classifier(rows), "time_model": evaluate_time_model(rows)}
    if llm_sample:
        results["llm_intake"] = evaluate_llm(rows, llm_sample)
        print(f"LLM intake: accuracy={results['llm_intake']['accuracy']} on {llm_sample} rows")
    c, t = results["classifier"], results["time_model"]
    print(f"Classifier: accuracy={c['accuracy']} precision={c['precision']} recall={c['recall']} f1={c['f1']}")
    print(f"Time model: MAE={t['mae_days']} days (baseline {t['baseline_mae_days']}), R2={t['r2']}")
    return results
