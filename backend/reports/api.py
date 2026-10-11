"""GET /api/reports/weekly/?end=YYYY-MM-DD  (admin) -> the weekly PDF report."""
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.views import APIView

from complaints.permissions import IsAdmin

from .weekly import build_weekly_pdf


class WeeklyReportView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        end_day = parse_date(request.query_params.get("end", "")) or timezone.localdate()
        pdf = build_weekly_pdf(end_day=end_day)
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="campusfix-weekly-{end_day}.pdf"'
        return response
