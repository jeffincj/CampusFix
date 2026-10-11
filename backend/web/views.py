"""Student-facing HTML pages: home, register, login, logout, dashboard."""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from accounts.forms import LoginForm, StudentRegisterForm
from complaints.models import Complaint
from complaints.services import visible_complaints


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
            messages.success(request, _("Welcome to CampusFix! Your account is ready."))
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
    Role-aware landing page after login: counts per status and the latest
    complaints this user can see (own / department / all).
    Staff and admins also get the React dashboard in Phase 7.
    """
    complaints = visible_complaints(request.user)
    counts = {status: complaints.filter(status=status).count() for status in Complaint.Status.values}
    context = {
        "counts": counts,
        "total": sum(counts.values()),
        "recent": complaints[:5],
    }
    return render(request, "web/dashboard.html", context)


def dashboard_app(request, path=""):
    """
    Serve the React dashboard (built with "npm run build"). Every /dashboard/... URL returns
    the same index.html; React Router then shows the right page in the browser.
    """
    index = settings.FRONTEND_DIST / "dashboard" / "index.html"
    if not index.exists():
        return HttpResponse(
            "The dashboard is not built yet. Run 'npm run build' in frontend/, "
            "or use the Vite dev server: http://localhost:5173/dashboard/",
            status=503, content_type="text/plain",
        )
    return FileResponse(open(index, "rb"), content_type="text/html")
