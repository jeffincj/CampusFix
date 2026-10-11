"""
AI / analytics API endpoints.

GET /api/hotspots/   DBSCAN clusters of complaints (staff: own department, admin: all)
GET /api/spikes/     Isolation Forest alerts on complaints per hour
GET /api/metrics/    model evaluation results (admin)
"""
from rest_framework.response import Response
from rest_framework.views import APIView

from complaints.permissions import IsAdmin, IsStaffOrAdmin
from complaints.services import visible_complaints

from .ml.hotspots import hotspots_for
from .ml.spikes import spikes_for
from .models import LLMCallLog, ModelMetric


def int_param(request, name, default, low, high):
    """Read an integer query parameter and keep it inside [low, high]."""
    value = request.query_params.get(name, "")
    number = int(value) if value.isdigit() else default
    return max(low, min(number, high))


class HotspotsView(APIView):
    permission_classes = [IsStaffOrAdmin]

    def get(self, request):
        days = int_param(request, "days", 30, 1, 365)
        min_samples = int_param(request, "min_samples", 4, 2, 50)
        clusters = hotspots_for(visible_complaints(request.user), days=days, min_samples=min_samples)
        return Response({"days": days, "hotspots": clusters})


class SpikesView(APIView):
    permission_classes = [IsStaffOrAdmin]

    def get(self, request):
        days = int_param(request, "days", 14, 2, 60)
        min_count = int_param(request, "min_count", 5, 2, 100)
        return Response({"days": days, "spikes": spikes_for(visible_complaints(request.user), days=days, min_count=min_count)})


class MetricsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        latest = {}
        for name in ("classifier", "time_model", "llm_intake"):
            row = ModelMetric.objects.filter(model_name=name).first()  # newest first
            latest[name] = row and {"metrics": row.metrics, "n_train": row.n_train, "n_test": row.n_test,
                                    "created_at": row.created_at, "notes": row.notes}
        return Response({"models": latest, "llm": llm_stats(), "agreement": agreement_stats()})


def llm_stats(last_n=1000):
    """Latency and cost of the most recent LLM calls (from the llm_calls table)."""
    calls = list(LLMCallLog.objects.all()[:last_n])
    if not calls:
        return {"calls": 0}
    ok = [c for c in calls if c.success]
    latencies = sorted(c.latency_ms for c in ok) or [0]
    by_purpose = {}
    for c in calls:
        row = by_purpose.setdefault(c.purpose, {"calls": 0, "cost_usd": 0.0})
        row["calls"] += 1
        row["cost_usd"] = round(row["cost_usd"] + float(c.cost_usd), 6)
    total_cost = sum(float(c.cost_usd) for c in calls)
    return {
        "calls": len(calls),
        "success_rate": round(len(ok) / len(calls), 4),
        "avg_latency_ms": round(sum(latencies) / len(latencies)),
        "p95_latency_ms": latencies[min(len(latencies) - 1, int(0.95 * len(latencies)))],
        "total_cost_usd": round(total_cost, 6),
        "avg_cost_usd": round(total_cost / len(calls), 6),
        "input_tokens": sum(c.input_tokens for c in calls),
        "output_tokens": sum(c.output_tokens for c in calls),
        "by_purpose": by_purpose,
    }


def agreement_stats():
    """How often the LLM and the classifier agreed on real submissions."""
    from complaints.models import Complaint

    both = Complaint.objects.exclude(llm_category="").exclude(ml_category="")
    total = both.count()
    agreed = sum(1 for llm, ml in both.values_list("llm_category", "ml_category") if llm == ml)
    return {
        "complaints_with_both": total,
        "agreement_rate": round(agreed / total, 4) if total else None,
        "needs_review_open": Complaint.objects.filter(needs_review=True, status__in=["open", "in_progress"]).count(),
    }


class ClassifyView(APIView):
    """
    POST /api/ai/classify/ {"text": "..."}  (staff/admin)
    Runs guardrails, the LLM and the classifier on a text WITHOUT saving it,
    and returns both answers side by side.
    """

    permission_classes = [IsStaffOrAdmin]

    def post(self, request):
        import time

        from . import guardrails, intake
        from .ml.train_classifier import predict

        text = str(request.data.get("text", "")).strip()
        if not 5 <= len(text) <= 2000:
            return Response({"detail": "text must be 5 to 2000 characters."}, status=400)

        ml = predict(text)
        check = guardrails.check_complaint("", text, classifier_confidence=ml.confidence if ml else None)

        started = time.monotonic()
        try:
            llm = {"result": intake.extract(text), "error": None}
        except intake.IntakeError as error:
            llm = {"result": None, "error": str(error)}
        llm["latency_ms"] = int((time.monotonic() - started) * 1000)

        classifier = None
        if ml:
            top = sorted(ml.probabilities.items(), key=lambda kv: -kv[1])[:3]
            classifier = {"label": ml.label, "confidence": round(ml.confidence, 4),
                          "top": [{"label": k, "probability": round(v, 4)} for k, v in top]}

        return Response({
            "guardrails": {"allowed": check.allowed, "code": check.code, "message": check.message},
            "llm": llm,
            "classifier": classifier,
            "agree": bool(llm["result"] and classifier and llm["result"]["category"] == classifier["label"]),
            "fallback": intake.rule_based_intake(text),
        })
