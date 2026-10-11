"""
The AI pipeline that runs when a student submits a complaint.

1. Guardrails      block spam / abuse / injection / off-topic text (clear message to the student)
2. LLM intake      strict JSON {category, urgency, location, summary, language}, validated, 1 retry
3. Classifier      TF-IDF + Logistic Regression; if it disagrees with the LLM -> needs_review
4. Duplicates      embedding + FAISS; similarity >= 0.85 with an open complaint -> duplicate_links
5. Time model      Random Forest -> predicted_days
6. Save            everything in the database

If the LLM fails, the classifier decides; if both are missing, the student's
category hint is used. A failure in steps 4-5 is logged and skipped, so a
student can always submit.
"""
import logging
from dataclasses import dataclass

from django.utils import timezone

from complaints import services

from . import embeddings, guardrails, intake
from .campus import locate
from .ml import train_classifier, train_time_model
from .ml.common import complaint_text

logger = logging.getLogger(__name__)


class GuardrailError(Exception):
    def __init__(self, result):
        super().__init__(result.message)
        self.result = result


@dataclass
class SubmissionResult:
    complaint: object
    duplicate_of: object = None
    similarity: float = 0.0


def safe_classify(text):
    try:
        return train_classifier.predict(text)
    except Exception:
        logger.exception("Classifier failed")
        return None


def submit_complaint(student, title, description, location="", block="", category="", llm=None):
    text = complaint_text(title, description)

    # Step 3 runs first because the off-topic guardrail uses the classifier's confidence.
    ml = safe_classify(text)

    # Step 1: guardrails
    check = guardrails.check_complaint(title, description, student, ml.confidence if ml else None)
    if not check.allowed:
        raise GuardrailError(check)

    # Step 2: LLM intake (falls back to rules if the LLM is off or fails)
    try:
        llm_data = intake.extract(text, client=llm)
    except intake.IntakeError as error:
        logger.info("LLM intake unavailable, using fallback: %s", error)
        llm_data = None
    rules = intake.rule_based_intake(text, location)

    if llm_data:
        final_category, source = llm_data["category"], "llm"
        urgency, language, summary = llm_data["urgency"], llm_data["language"], llm_data["summary"]
        location = location or llm_data["location"]
    else:
        final_category, source = (ml.label, "classifier") if ml else (category, "student")
        urgency, language, summary = rules["urgency"], rules["language"], ""
        location = location or rules["location"]

    if not block:
        place = locate(location, text)
        block = place[1] if place else ""

    complaint = services.create_complaint(
        student,
        title=title, description=description, location=location[:200], block=block, category=final_category,
        urgency=urgency, language=language, summary=summary[:300], ai_source=source,
        llm_category=llm_data["category"] if llm_data else "",
        ml_category=ml.label if ml else "", ml_confidence=round(ml.confidence, 4) if ml else None,
        # Step 3: the two AI opinions disagree -> a human should check the routing
        needs_review=bool(llm_data and ml and llm_data["category"] != ml.label),
    )
    result = SubmissionResult(complaint)

    # Step 4: duplicate detection
    try:
        vector = embeddings.embed_text(text)
        complaint.embedding = embeddings.to_bytes(vector)
        complaint.embedding_model = embeddings.get_embedder().name
        found = embeddings.find_duplicate(complaint, vector)
        if found:
            original, similarity = found
            embeddings.link_duplicate(original, complaint, similarity)
            result.duplicate_of, result.similarity = original, similarity
    except Exception:
        logger.exception("Duplicate check failed for complaint %s", complaint.pk)

    # Step 5: resolution time
    try:
        complaint.predicted_days = train_time_model.predict_days(
            complaint.category, complaint.urgency, complaint.block, timezone.localtime(complaint.created_at), text
        )
    except Exception:
        logger.exception("Time prediction failed for complaint %s", complaint.pk)

    # Step 6: save the AI results
    complaint.save(update_fields=["embedding", "embedding_model", "predicted_days", "updated_at"])
    return result
