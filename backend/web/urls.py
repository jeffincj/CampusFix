"""URL routes for the HTML pages."""
from django.urls import path

from . import complaint_views, views

app_name = "web"  # lets templates use names like {% url 'web:login' %}

urlpatterns = [
    # Accounts
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.CampusLoginView.as_view(), name="login"),
    path("logout/", views.CampusLogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard_app, name="dashboard_app"),  # React dashboard (staff/admin)
    path("dashboard/<path:path>", views.dashboard_app),
    path("home/", views.dashboard, name="dashboard"),  # student/role landing page
    # Complaints
    path("complaints/", complaint_views.complaint_list, name="complaint_list"),
    path("complaints/new/", complaint_views.complaint_create, name="complaint_create"),
    path("complaints/preview/", complaint_views.complaint_preview, name="complaint_preview"),
    path("complaints/status.json", complaint_views.complaint_status_json, name="complaint_status_json"),
    path("complaints/<int:pk>/", complaint_views.complaint_detail, name="complaint_detail"),
    path("complaints/<int:pk>/edit/", complaint_views.complaint_edit, name="complaint_edit"),
    path("complaints/<int:pk>/delete/", complaint_views.complaint_delete, name="complaint_delete"),
    path("complaints/<int:pk>/status/", complaint_views.complaint_update_status, name="complaint_update_status"),
    path("complaints/<int:pk>/feedback/", complaint_views.complaint_feedback, name="complaint_feedback"),
]
