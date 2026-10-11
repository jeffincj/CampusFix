"""URL routes for the student HTML pages."""
from django.urls import path

from . import views

app_name = "web"  # lets templates use names like {% url 'web:login' %}

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.CampusLoginView.as_view(), name="login"),
    path("logout/", views.CampusLogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
