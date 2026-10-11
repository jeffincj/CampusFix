"""Top-level URL routes."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),  # Django admin panel
    path("api/", include("config.api_urls")),  # REST API (JWT)
    path("", include("web.urls")),  # student-facing HTML pages
]
