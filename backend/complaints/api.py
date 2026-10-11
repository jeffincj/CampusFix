"""
Complaints REST API.

GET    /api/complaints/          list (filtered by role + query params)
POST   /api/complaints/          create (students only)
GET    /api/complaints/{id}/     detail with status history
PATCH  /api/complaints/{id}/     update (allowed fields depend on role)
GET    /api/complaints/stats/    counts for dashboard charts (staff/admin)
GET    /api/departments/         list of departments
"""
from collections import Counter
from datetime import datetime, time, timedelta

from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from . import services
from .models import Complaint, Department
from .permissions import IsStaffOrAdmin, IsStudent
from .serializers import (
    ComplaintCreateSerializer,
    ComplaintDetailSerializer,
    ComplaintPatchSerializer,
    ComplaintSerializer,
    DepartmentSerializer,
)

# Fields the client may sort by: ?ordering=-created_at
ORDERING_FIELDS = {"created_at", "updated_at", "urgency", "status", "category", "duplicate_count", "id"}


def start_of_day(day):
    """A date -> timezone-aware datetime at 00:00 in the campus time zone."""
    return timezone.make_aware(datetime.combine(day, time.min))


class ComplaintViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """One class handles list, create, retrieve, partial update and stats."""

    http_method_names = ["get", "post", "patch", "head", "options"]  # no PUT, no DELETE

    def get_queryset(self):
        # The role rule: student -> own, staff -> department, admin -> all.
        # Anything outside this queryset returns 404, so other users' complaints stay hidden.
        return services.visible_complaints(self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return ComplaintCreateSerializer
        if self.action == "retrieve":
            return ComplaintDetailSerializer
        return ComplaintSerializer

    def get_permissions(self):
        # Extra role checks on top of "must be logged in" (the default).
        if self.action == "create":
            return [IsStudent()]
        if self.action == "stats":
            return [IsStaffOrAdmin()]
        return super().get_permissions()

    # --- list -----------------------------------------------------------------

    def filter_queryset(self, queryset):
        """Apply ?status=&category=&urgency=&department=&block=&needs_review=&q=&from=&to=&ordering="""
        params = self.request.query_params

        for field in ("status", "category", "urgency", "block"):
            if params.get(field):
                queryset = queryset.filter(**{field: params[field]})
        if params.get("department", "").isdigit():
            queryset = queryset.filter(department_id=int(params["department"]))
        if params.get("needs_review") in ("true", "false"):
            queryset = queryset.filter(needs_review=params["needs_review"] == "true")
        if params.get("q"):
            q = params["q"].strip()
            queryset = queryset.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(location__icontains=q))

        # Date range. We compare with datetimes (not __date) so it works on MySQL
        # even when MySQL's time-zone tables are not installed.
        date_from, date_to = parse_date(params.get("from", "")), parse_date(params.get("to", ""))
        if date_from:
            queryset = queryset.filter(created_at__gte=start_of_day(date_from))
        if date_to:
            queryset = queryset.filter(created_at__lt=start_of_day(date_to + timedelta(days=1)))

        ordering = params.get("ordering", "-created_at")
        if ordering.lstrip("-") in ORDERING_FIELDS:
            queryset = queryset.order_by(ordering)
        return queryset

    # --- create ---------------------------------------------------------------

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        complaint = services.create_complaint(request.user, **serializer.validated_data)
        return Response(ComplaintDetailSerializer(complaint).data, status=status.HTTP_201_CREATED)

    # --- partial update -------------------------------------------------------

    def partial_update(self, request, *args, **kwargs):
        complaint = self.get_object()  # 404 if not visible

        # 1. Role check: is the user allowed to touch each field they sent?
        allowed = services.allowed_patch_fields(request.user, complaint)
        if not allowed:
            raise PermissionDenied("You cannot update this complaint.")
        not_allowed = sorted(set(request.data) - allowed)
        if not_allowed:
            raise PermissionDenied(f"You cannot change: {', '.join(not_allowed)}.")

        # 2. Value check: types, choices, lengths.
        serializer = ComplaintPatchSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # 3. Apply, using the same workflow rules as the HTML pages.
        try:
            services.update_complaint(complaint, request.user, serializer.validated_data)
        except services.StatusChangeError as error:
            raise ValidationError({"status": [str(error)]})

        complaint.refresh_from_db()
        return Response(ComplaintDetailSerializer(complaint).data)

    # --- stats ----------------------------------------------------------------

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Counts for the dashboard charts, limited to what the user can see
        (staff: own department, admin: everything).
        """
        queryset = self.get_queryset()

        def count_by(field):
            rows = queryset.values(field).annotate(count=Count("id")).order_by("-count")
            return [{"key": row[field] or "unknown", "count": row["count"]} for row in rows]

        return Response(
            {
                "total": queryset.count(),
                "by_category": count_by("category"),
                "by_status": count_by("status"),
                "by_urgency": count_by("urgency"),
                "by_block": count_by("block"),
                "by_week": self.weekly_counts(queryset, weeks=self.weeks_param(request)),
            }
        )

    @staticmethod
    def weeks_param(request):
        """Read ?weeks=N safely (default 12)."""
        value = request.query_params.get("weeks", "12")
        return int(value) if value.isdigit() else 12

    @staticmethod
    def weekly_counts(queryset, weeks=12):
        """
        Complaints per week (weeks start on Monday) for the last N weeks.
        Grouped in Python on purpose: SQL week functions with time zones
        need extra MySQL setup, and a few thousand dates are cheap to count here.
        """
        weeks = max(1, min(weeks, 52))
        today = timezone.localdate()
        this_monday = today - timedelta(days=today.weekday())
        first_monday = this_monday - timedelta(weeks=weeks - 1)

        dates = queryset.filter(created_at__gte=start_of_day(first_monday)).values_list("created_at", flat=True)
        counter = Counter()
        for created in dates:
            day = timezone.localtime(created).date()
            counter[day - timedelta(days=day.weekday())] += 1  # Monday of that week

        return [
            {"week": (first_monday + timedelta(weeks=i)).isoformat(), "count": counter[first_monday + timedelta(weeks=i)]}
            for i in range(weeks)
        ]



class DepartmentListView(generics.ListAPIView):
    """GET /api/departments/ -> all departments (used for dropdowns and filters)."""

    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    pagination_class = None
