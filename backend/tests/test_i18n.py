"""Tests for the language switcher (English / Tamil / Malayalam) and the student AI card."""
import pytest
from django.urls import reverse

from ai.pipeline import submit_complaint
from complaints import services

pytestmark = pytest.mark.django_db


def in_language(client, code):
    """Choose a language the same way the switcher does (POST to Django's set_language view)."""
    response = client.post("/i18n/setlang/", {"language": code, "next": "/"})
    assert response.status_code == 302
    return client


# --- Language switcher ----------------------------------------------------------

def test_default_is_english(client):
    page = client.get(reverse("web:home")).content.decode()
    assert "Report campus problems in your own language" in page
    assert '<html lang="en">' in page


@pytest.mark.parametrize("code, heading, register", [
    ("ta", "வளாகப் பிரச்சினைகளை உங்கள் சொந்த மொழியில் புகாரளியுங்கள்", "பதிவு செய்"),
    ("ml", "ക്യാമ്പസ് പ്രശ്നങ്ങൾ നിങ്ങളുടെ സ്വന്തം ഭാഷയിൽ റിപ്പോർട്ട് ചെയ്യൂ", "രജിസ്റ്റർ ചെയ്യുക"),
])
def test_switch_language(client, code, heading, register):
    page = in_language(client, code).get(reverse("web:home")).content.decode()
    assert heading in page
    assert register in page
    assert f'<html lang="{code}">' in page


def test_switcher_lists_three_languages(client):
    page = client.get(reverse("web:login")).content.decode()
    for name in ("English", "தமிழ்", "മലയാളം"):
        assert name in page


def test_form_labels_and_js_messages_translated(client):
    page = in_language(client, "ta").get(reverse("web:register")).content.decode()
    assert "மாணவர் பதிவு" in page  # "Student registration"
    assert "கடவுச்சொல் உறுதிப்படுத்தல்" in page  # "Password confirmation"
    assert "இந்தப் புலம் தேவை." in page  # JS message "This field is required."


def test_status_labels_translated(client, complaint, student):
    client.force_login(student)
    page = in_language(client, "ml").get(reverse("web:complaint_list")).content.decode()
    assert "തുറന്നത്" in page  # "Open"
    data = client.get(reverse("web:complaint_status_json") + f"?ids={complaint.pk}").json()
    assert data["complaints"][0]["status_display"] == "തുറന്നത്"  # live refresh is translated too


def test_guardrail_message_in_tamil(client, student):
    client.force_login(student)
    in_language(client, "ta")
    page = client.post(reverse("web:complaint_create"),
                       {"title": "Offer", "description": "Visit www.cheap-deals.example for discounts"}).content.decode()
    assert "புகார்களில் இணைப்புகள் அனுமதிக்கப்படவில்லை" in page


def test_success_message_translated(client, student):
    client.force_login(student)
    in_language(client, "ml")
    response = client.post(reverse("web:complaint_create"),
                           {"title": "Fan", "description": "Fan not working in B Block hostel room 12", "category": "HOSTEL"},
                           follow=True)
    assert "സമർപ്പിച്ചു" in response.content.decode()  # "submitted"


def test_api_stays_english_by_default(api_as, student):
    response = api_as(student).post("/api/complaints/", {"title": "x", "description": "The warden is a bastard and rude"},
                                    format="json")
    assert response.data["detail"].startswith("Please remove abusive language")


def test_compile_translations_command(tmp_path, settings):
    import io
    import shutil

    from django.core.management import call_command

    shutil.copytree(settings.LOCALE_PATHS[0], tmp_path / "locale")
    settings.LOCALE_PATHS = [tmp_path / "locale"]
    out = io.StringIO()
    call_command("compile_translations", stdout=out)
    assert "ta: 100% translated" in out.getvalue() and "ml: 100% translated" in out.getvalue()


# --- Student AI card --------------------------------------------------------------

def test_student_sees_ai_card(client, student, it_dept):
    complaint = submit_complaint(student, title="Wifi illa", category="IT",
                                 description="Library il wifi kittunnilla, assignment submit cheyyan pattunnilla").complaint
    client.force_login(student)
    page = client.get(reverse("web:complaint_detail", args=[complaint.pk])).content.decode()
    assert "How CampusFix AI understood your complaint" in page
    assert "IT Services" in page  # department it was sent to
    assert "Mixed language" in page  # language detected
    assert "Your choice" in page  # who decided (no AI models in this test)
    assert "AI routing (staff view)" not in page  # internal details stay hidden from students


def test_ai_card_shows_duplicate_link(client, student, other_student):
    text = {"title": "Wi-Fi not working", "description": "Wi-Fi is not working in B Block Hostel since evening.",
            "block": "B Block"}
    submit_complaint(student, **text)
    duplicate = submit_complaint(other_student, **text).complaint
    client.force_login(other_student)
    page = client.get(reverse("web:complaint_detail", args=[duplicate.pk])).content.decode()
    assert "Another student already reported this problem (100% similar)" in page


def test_ai_card_translated(client, student, hostel):
    complaint = services.create_complaint(student, title="Fan", description="Fan broken in room", category="HOSTEL",
                                          language="ta", ai_source="classifier", predicted_days=2.5)
    client.force_login(student)
    page = in_language(client, "ta").get(reverse("web:complaint_detail", args=[complaint.pk])).content.decode()
    assert "CampusFix AI உங்கள் புகாரை எப்படிப் புரிந்துகொண்டது" in page
    assert "விடுதி அலுவலகம்" in page  # "Hostel Office"
    assert "சுமார் 2.5 நாட்கள்" in page  # "about 2.5 days"
    assert "AI வகைப்படுத்தி" in page  # "AI classifier"
    assert "புகார் சமர்ப்பிக்கப்பட்டது" in page  # history note "Complaint submitted"


def test_staff_still_see_routing_details(client, complaint, hostel_staff):
    client.force_login(hostel_staff)
    page = client.get(reverse("web:complaint_detail", args=[complaint.pk])).content.decode()
    assert "How CampusFix AI understood your complaint" in page
    assert "AI routing (staff view)" in page
