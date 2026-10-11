"""Top-level URL routes."""
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path


def health(request):
    """GET /healthz/ -> used by Docker and Render to check the app and database are up."""
    try:
        connection.ensure_connection()
        return JsonResponse({"status": "ok", "database": "ok"})
    except Exception:
        return JsonResponse({"status": "error", "database": "unreachable"}, status=503)


urlpatterns = [
    path("healthz/", health),
    path("admin/", admin.site.urls),  # Django admin panel
    path("api/", include("config.api_urls")),  # REST API (JWT)
    path("", include("web.urls")),  # student-facing HTML pages
]
