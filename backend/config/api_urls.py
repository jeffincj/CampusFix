"""All REST API routes, mounted under /api/."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.api import LoginView, MeView, RefreshView, RegisterView
from ai.api import (
    ChatView,
    ClassifyView,
    DocumentDetailView,
    DocumentsView,
    HotspotsView,
    MetricsView,
    SpikesView,
)
from complaints.api import ComplaintViewSet, DepartmentListView
from reports.api import WeeklyReportView

# The router creates /complaints/, /complaints/{id}/ and /complaints/stats/ from the ViewSet.
router = DefaultRouter()
router.register("complaints", ComplaintViewSet, basename="complaint")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="api-register"),
    path("auth/login/", LoginView.as_view(), name="api-login"),
    path("auth/refresh/", RefreshView.as_view(), name="api-refresh"),
    path("auth/me/", MeView.as_view(), name="api-me"),
    path("departments/", DepartmentListView.as_view(), name="api-departments"),
    path("hotspots/", HotspotsView.as_view(), name="api-hotspots"),
    path("spikes/", SpikesView.as_view(), name="api-spikes"),
    path("metrics/", MetricsView.as_view(), name="api-metrics"),
    path("ai/classify/", ClassifyView.as_view(), name="api-classify"),
    path("chat/", ChatView.as_view(), name="api-chat"),
    path("documents/", DocumentsView.as_view(), name="api-documents"),
    path("documents/<int:pk>/", DocumentDetailView.as_view(), name="api-document-detail"),
    path("reports/weekly/", WeeklyReportView.as_view(), name="api-weekly-report"),
    path("", include(router.urls)),
]
