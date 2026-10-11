"""Phase 4 tests: sample data, classifier, time model, hotspots, spikes, evaluation, sample loader."""
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from ai.campus import locate
from ai.ml import evaluate, train_classifier, train_time_model
from ai.ml.hotspots import find_hotspots
from ai.ml.spikes import detect_spikes, hourly_counts
from ai.models import ModelMetric
from complaints.models import Complaint


# --- Synthetic data -----------------------------------------------------------

def test_sample_csv_shape(sample_rows):
    assert len(sample_rows) == 300
    assert {r["category"] for r in sample_rows} == set(Complaint.Category.values)
    assert {r["language"] for r in sample_rows} == {"en", "ta", "ml", "mixed"}
    assert all(r["synthetic"] == "yes" for r in sample_rows)


def test_generator_is_deterministic():
    from data.generate_sample_data import generate

    assert generate()[:5] == generate()[:5]


def test_campus_locate():
    assert locate("near B Block hostel room 12")[1] == "B Block"
    assert locate("Girls hostel washroom")[0] == "Girls Hostel"  # longer alias wins over "hostel"
    assert locate("somewhere unknown") is None


# --- Classifier ---------------------------------------------------------------

def test_classifier_trains_saves_and_predicts(ml_dir, trained_classifier):
    path = train_classifier.save(trained_classifier)
    assert path.parent == ml_dir and path.exists()
    prediction = train_classifier.predict("Wi-Fi not working in A block hostel")
    assert prediction.label == "IT"
    assert 0 < prediction.confidence <= 1
    assert abs(sum(prediction.probabilities.values()) - 1) < 1e-6


@pytest.mark.parametrize("text, label", [
    ("விடுதியில் வைஃபை வேலை செய்யவில்லை", "IT"),  # Tamil
    ("മെസ്സിലെ ഭക്ഷണത്തിൽ പ്രാണി", "MESS"),  # Malayalam
    ("bus daily late ah varudhu", "TRANSPORT"),  # Tanglish
    ("washroom clean pannala romba smell", "SANITATION"),
])
def test_classifier_multilingual(trained_classifier, text, label):
    assert train_classifier.predict(text, model=trained_classifier).label == label


def test_predict_without_model_returns_none(ml_dir):
    assert train_classifier.predict("anything") is None


# --- Time model ---------------------------------------------------------------

def test_time_model_trains_and_predicts(ml_dir, sample_rows):
    model = train_time_model.train(sample_rows)
    train_time_model.save(model)
    now = timezone.now()
    critical = train_time_model.predict_days("SECURITY", "critical", "Main Gate", now, "ragging near gate")
    slow = train_time_model.predict_days("LAB", "low", "Academic Block 1", now, "projector not working")
    assert 0 < critical < slow  # learned: critical security issues close faster than low-priority lab issues


# --- Evaluation ---------------------------------------------------------------

@pytest.mark.django_db
def test_evaluate_saves_metrics(sample_rows):
    results = evaluate.main()
    clf = results["classifier"]
    assert clf["accuracy"] > 0.85
    assert len(clf["confusion_matrix"]) == 8 and len(clf["labels"]) == 8
    assert sum(map(sum, clf["confusion_matrix"])) == 60  # 20% test split of 300
    assert results["time_model"]["mae_days"] < results["time_model"]["baseline_mae_days"]
    assert set(ModelMetric.objects.values_list("model_name", flat=True)) == {"classifier", "time_model"}


# --- Hotspots (DBSCAN) --------------------------------------------------------

def point(i, category, x, y):
    return {"id": i, "category": category, "place": f"P{x}", "block": "B", "x": x, "y": y,
            "status": "open", "created_at": timezone.now()}


def test_hotspots_cluster_by_location_and_category():
    points = [point(i, "HOSTEL", 100 + i, 400) for i in range(6)]  # dense group
    points += [point(10 + i, "IT", 100 + i, 400) for i in range(2)]  # same place, other category, too few
    points += [point(20, "HOSTEL", 500, 0)]  # isolated -> noise
    clusters = find_hotspots(points, eps=70, min_samples=4)
    assert len(clusters) == 1
    assert clusters[0]["category"] == "HOSTEL" and clusters[0]["count"] == 6
    assert 20 not in clusters[0]["complaint_ids"]


def test_hotspots_need_enough_points():
    assert find_hotspots([point(1, "IT", 0, 0)]) == []


# --- Spikes (Isolation Forest) ------------------------------------------------

def test_spike_detected():
    end = timezone.localtime().replace(minute=30)
    normal = [end - timedelta(hours=h) for h in range(0, 14 * 24, 5)]  # ~1 complaint every 5 hours
    spike_hour = end - timedelta(days=2)
    spike = [spike_hour + timedelta(minutes=m) for m in range(0, 24, 2)]  # 12 in one hour
    spikes = detect_spikes(normal + spike, end=end, days=14, min_count=5)
    assert len(spikes) == 1
    assert spikes[0]["count"] == 12


def test_no_spike_in_calm_data():
    end = timezone.now()
    calm = [end - timedelta(hours=h) for h in range(0, 14 * 24, 3)]
    assert detect_spikes(calm, end=end) == []


def test_hourly_counts_cover_every_hour():
    end = timezone.now()
    series = hourly_counts([end], end, days=2)
    assert len(series) == 48 and series[-1][1] == 1


# --- Sample loader + API ------------------------------------------------------

@pytest.mark.django_db
def test_load_sample_data_and_analytics_api(api_as, admin_user, it_staff, student):
    call_command("load_sample_data")
    assert Complaint.objects.count() == 300
    newest = Complaint.objects.order_by("-created_at").first().created_at
    assert abs(timezone.now() - newest) < timedelta(hours=1)
    # History matches status
    closed = Complaint.objects.filter(status="closed").first()
    assert list(closed.history.values_list("new_status", flat=True)) == ["open", "in_progress", "resolved", "closed"]

    admin = api_as(admin_user)
    hotspots = admin.get("/api/hotspots/").data["hotspots"]
    assert hotspots and hotspots[0]["count"] >= hotspots[-1]["count"]
    spikes = admin.get("/api/spikes/").data["spikes"]
    assert spikes and spikes[0]["categories"][0]["category"] == "IT"  # the synthetic Wi-Fi outage

    # Staff only see their own department's hotspots
    staff_hotspots = api_as(it_staff).get("/api/hotspots/").data["hotspots"]
    assert {h["category"] for h in staff_hotspots} <= {"IT"}

    # Students cannot use analytics; metrics are admin-only
    assert api_as(student).get("/api/hotspots/").status_code == 403
    assert api_as(it_staff).get("/api/metrics/").status_code == 403


@pytest.mark.django_db
def test_metrics_api(api_as, admin_user):
    ModelMetric.objects.create(model_name="classifier", metrics={"accuracy": 0.9}, n_train=240, n_test=60)
    data = api_as(admin_user).get("/api/metrics/").data
    assert data["models"]["classifier"]["metrics"]["accuracy"] == 0.9
    assert data["models"]["time_model"] is None


@pytest.mark.django_db
def test_train_models_if_needed(ml_dir):
    import io

    call_command("train_models", "--if-needed", stdout=io.StringIO())
    assert (ml_dir / "classifier.joblib").exists() and (ml_dir / "time_model.joblib").exists()
    assert ModelMetric.objects.count() == 2
    call_command("train_models", "--if-needed", stdout=io.StringIO())  # second run does nothing
    assert ModelMetric.objects.count() == 2
