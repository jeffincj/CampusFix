"""Phase 8 tests: weekly PDF report, report API, health check, dashboard serving."""
import io
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone
from pypdf import PdfReader

from complaints import services
from complaints.models import Complaint
from reports.weekly import build_weekly_pdf, collect, english_line

pytestmark = pytest.mark.django_db


@pytest.fixture
def week_of_complaints(student, hostel_staff):
    made = [
        services.create_complaint(student, title="Fan broken", description="Fan broken in room", category="HOSTEL", block="B Block"),
        services.create_complaint(student, title="Wifi down", description="Wifi down in library", category="IT", block="Library", urgency="critical"),
        services.create_complaint(student, title="விடுதியில் தண்ணீர் இல்லை", description="தண்ணீர் இல்லை", category="HOSTEL",
                                  location="C Block Hostel", urgency="high"),
    ]
    services.change_status(made[0], "resolved", hostel_staff)
    return made


def test_collect_numbers(week_of_complaints):
    data = collect(Complaint.objects.all(), timezone.localdate())
    assert data["this"]["new"] == 3
    assert data["this"]["resolved"] == 1
    assert data["this"]["critical"] == 1
    assert data["previous"]["new"] == 0
    assert data["by_category"]["Hostel"] == 2
    assert sum(data["per_day"]) == 3 and len(data["per_day"]) == 14
    assert [c.urgency for c in data["urgent_open"]] == ["critical", "high"]


def test_pdf_has_three_pages_and_summary(week_of_complaints):
    pdf = build_weekly_pdf()
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) == 3
    text = reader.pages[0].extract_text()
    assert "Weekly report" in text and "New complaints" in text
    assert "Hostel problem at C Block Hostel" in text  # Tamil title replaced by an English line


def test_pdf_with_no_data():
    reader = PdfReader(io.BytesIO(build_weekly_pdf()))
    assert len(reader.pages) == 3
    assert "Nothing was resolved this week." in reader.pages[2].extract_text()


def test_english_line(week_of_complaints):
    fan, _, tamil = week_of_complaints
    assert english_line(fan) == "Fan broken"
    tamil.summary = "No water in C Block hostel."
    assert english_line(tamil) == "No water in C Block hostel."


def test_report_api_admin_only(api_as, admin_user, hostel_staff, week_of_complaints):
    response = api_as(admin_user).get("/api/reports/weekly/")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert api_as(hostel_staff).get("/api/reports/weekly/").status_code == 403


def test_report_api_end_date(api_as, admin_user, week_of_complaints):
    last_month = timezone.localdate() - timedelta(days=30)
    response = api_as(admin_user).get(f"/api/reports/weekly/?end={last_month}")
    assert f"campusfix-weekly-{last_month}.pdf" in response["Content-Disposition"]


def test_weekly_report_command(tmp_path, week_of_complaints):
    out = tmp_path / "report.pdf"
    call_command("weekly_report", "--out", str(out), stdout=io.StringIO())
    assert out.read_bytes().startswith(b"%PDF")


def test_health_check(client):
    response = client.get("/healthz/")
    assert response.status_code == 200 and response.json() == {"status": "ok", "database": "ok"}


def test_dashboard_served_or_explained(client, settings, tmp_path):
    settings.FRONTEND_DIST = tmp_path  # no build here
    response = client.get("/dashboard/complaints")
    assert response.status_code == 503 and b"npm run build" in response.content
    (tmp_path / "dashboard").mkdir()
    (tmp_path / "dashboard" / "index.html").write_text("<div id=root></div>")
    assert b"id=root" in b"".join(client.get("/dashboard/charts").streaming_content)
