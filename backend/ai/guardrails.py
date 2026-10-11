"""
Guardrails: block spam, abuse, prompt-injection and off-topic text
BEFORE it reaches the LLM or the database. Each check is plain Python
(fast, free, predictable) and returns a clear message for the student.
"""
import re
from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

MAX_COMPLAINTS_PER_HOUR = 5

# Strong abuse only. Words like "stupid wifi" are frustration, not abuse, so they are allowed.
# Extend this list (including Tamil/Malayalam terms) from real pilot data.
ABUSE_WORDS = ["fuck", "fucking", "motherfucker", "bitch", "bastard", "asshole", "slut", "whore"]

INJECTION_PATTERNS = [
    r"ignore (all |the )?(previous|above|earlier) (instructions|prompts?)",
    r"disregard (all |the )?(previous|above) ",
    r"system prompt",
    r"you are now ",
    r"act as (an? )?(admin|administrator|developer)",
    r"<\s*/?\s*(system|complaint)\s*>",
]

# Words that show the text is about the campus (English, Tamil, Malayalam, romanised).
CAMPUS_WORDS = [
    "hostel", "room", "mess", "food", "canteen", "wifi", "wi-fi", "internet", "lan", "portal", "lab", "class",
    "projector", "computer", "bus", "driver", "route", "transport", "water", "power", "current", "electric",
    "fan", "light", "switch", "tap", "leak", "toilet", "washroom", "bathroom", "garbage", "clean", "mosquito",
    "rat", "security", "gate", "outsider", "theft", "stolen", "ragging", "library", "warden", "campus",
    "college", "exam", "block", "ground", "lock", "cot", "bed", "smell", "dark", "safe",
    "விடுதி", "அறை", "உணவு", "சாப்பாடு", "தண்ணீர்", "மின்", "வைஃபை", "இணைய", "பேருந்து", "கழிவறை", "ஆய்வக",
    "வகுப்பு", "கல்லூரி", "குப்பை", "கொசு", "திருட",
    "ഹോസ്റ്റൽ", "മുറി", "ഭക്ഷണ", "വെള്ള", "കറന്റ്", "വൈഫൈ", "ഇന്റർനെറ്റ്", "ബസ്", "ലാബ", "ക്ലാസ", "കോളേജ്",
    "വാഷ്റൂം", "മാലിന്യ", "കൊതുക്", "മോഷണ",
    "vellam", "saapadu", "sapadu",
]

# Extra words allowed in the staff/admin chat (questions about complaints and rules).
CHAT_WORDS = [
    "complaint", "rule", "policy", "fine", "penalty", "curfew", "leave", "fee", "attendance", "allowed",
    "department", "status", "open", "resolved", "pending", "urgent", "hotspot", "spike", "how many", "count",
    "list", "show", "report", "week", "today", "student", "staff", "visitor", "timing", "deadline", "refund",
]


@dataclass
class GuardrailResult:
    allowed: bool
    code: str = "ok"  # ok | spam | abuse | injection | off_topic | rate_limit | repeat
    message: str = ""


OK = GuardrailResult(True)


def _contains_any(text, words):
    lowered = text.lower()
    # English words must match as whole words (plural allowed): "rat"/"rats" but not "rather".
    return any(
        re.search(rf"(?<![a-z]){re.escape(w)}(s|es)?(?![a-z])", lowered) if w.isascii() else w in lowered
        for w in words
    )


def check_injection(text):
    lowered = text.lower()
    if any(re.search(p, lowered) for p in INJECTION_PATTERNS):
        return GuardrailResult(False, "injection", "Please describe only the campus problem, without instructions to the system.")
    return OK


def check_spam(text):
    if re.search(r"https?://|www\.", text, re.IGNORECASE):
        return GuardrailResult(False, "spam", "Links are not allowed in complaints. Please describe the problem in words.")
    if re.search(r"(.)\1{7,}", text):  # e.g. "aaaaaaaaa" or "!!!!!!!!!"
        return GuardrailResult(False, "spam", "Your complaint looks like spam (repeated characters). Please write it normally.")
    words = re.findall(r"\S+", text.lower())
    if len(words) >= 6 and max(words.count(w) for w in set(words)) / len(words) > 0.5:
        return GuardrailResult(False, "spam", "Your complaint repeats the same word many times. Please write it normally.")
    letters = sum(ch.isalpha() for ch in text)
    if len(text) >= 10 and letters / len(text) < 0.4:
        return GuardrailResult(False, "spam", "Your complaint has too few words. Please describe the problem.")
    return OK


def check_abuse(text):
    lowered = text.lower()
    if any(re.search(rf"\b{re.escape(w)}\b", lowered) for w in ABUSE_WORDS):
        return GuardrailResult(False, "abuse", "Please remove abusive language. You can still report the problem politely.")
    return OK


def check_off_topic(text, classifier_confidence=None):
    """
    Off-topic = no campus word AND the classifier is not confident (< 0.5).
    Without a trained classifier we cannot judge, so we allow the text:
    blocking a real complaint is worse than letting one odd text through.
    """
    if _contains_any(text, CAMPUS_WORDS):
        return OK
    if classifier_confidence is None or classifier_confidence >= 0.5:
        return OK
    return GuardrailResult(False, "off_topic", "This does not look like a campus problem. Please mention what is wrong and where (hostel, mess, Wi-Fi, lab, bus, ...).")


def check_flooding(student, text, now=None):
    """Limit complaints per hour and block the same text sent twice in a day."""
    from complaints.models import Complaint

    now = now or timezone.now()
    recent = Complaint.objects.filter(student=student, created_at__gte=now - timedelta(hours=1)).count()
    if recent >= MAX_COMPLAINTS_PER_HOUR:
        return GuardrailResult(False, "rate_limit", "You have sent many complaints in the last hour. Please wait a little before sending more.")
    same = Complaint.objects.filter(student=student, created_at__gte=now - timedelta(days=1), description__iexact=text.strip())
    if same.exists():
        return GuardrailResult(False, "repeat", f"You already reported this (complaint #{same.first().pk}). You can track it there.")
    return OK


def check_complaint(title, description, student=None, classifier_confidence=None):
    """Run all complaint checks in order. Returns the first failure, or OK."""
    text = f"{title} {description}"
    for result in (check_injection(text), check_spam(text), check_abuse(text)):
        if not result.allowed:
            return result
    if student is not None:
        result = check_flooding(student, description)
        if not result.allowed:
            return result
    return check_off_topic(text, classifier_confidence)


def check_chat_question(question):
    """Staff/admin chat: block injection and questions that are not about complaints or college rules."""
    for result in (check_injection(question), check_abuse(question)):
        if not result.allowed:
            return result
    if not _contains_any(question, CAMPUS_WORDS + CHAT_WORDS):
        return GuardrailResult(False, "off_topic", "I can only answer questions about campus complaints and college rules.")
    return OK
