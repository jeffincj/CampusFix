"""Student-facing HTML pages: home, register, login, logout, dashboard."""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from accounts.forms import LoginForm, StudentRegisterForm


def home(request):
    """Landing page. Logged-in users go straight to their dashboard."""
    if request.user.is_authenticated:
        return redirect("web:dashboard")
    return render(request, "web/home.html")


def register(request):
    """Show the sign-up form (GET) or create a student account (POST)."""
    if request.user.is_authenticated:
        return redirect("web:dashboard")

    if request.method == "POST":
        form = StudentRegisterForm(request.POST)
        if form.is_valid():  # server-side validation (JS validation is only a helper)
            user = form.save()
            login(request, user)  # log in right after sign-up
            messages.success(request, "Welcome to CampusFix! Your account is ready.")
            return redirect("web:dashboard")
    else:
        form = StudentRegisterForm()

    return render(request, "web/register.html", {"form": form})


class CampusLoginView(LoginView):
    """Django's built-in login view with our template and form."""

    template_name = "web/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class CampusLogoutView(LogoutView):
    """Logs out on POST (Django 5 requires POST for logout, which blocks CSRF tricks)."""


@login_required
def dashboard(request):
    """
    Role-aware landing page after login.
    Students will submit/track complaints here (Phase 2).
    Staff and admins will use the React dashboard (Phase 7).
    """
    return render(request, "web/dashboard.html")
