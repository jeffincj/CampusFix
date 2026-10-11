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
from .models import ModelMetric


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
        return Response({"models": latest})
