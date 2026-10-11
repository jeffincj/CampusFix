"""Tables for the AI features: model metrics (more tables are added in later phases)."""
from django.db import models


class ModelMetric(models.Model):
    """One evaluation run of one model (accuracy, confusion matrix, MAE, ...)."""

    model_name = models.CharField(max_length=50)  # "classifier", "time_model", "llm_intake"
    metrics = models.JSONField()  # all numbers for that run
    n_train = models.PositiveIntegerField(default=0)
    n_test = models.PositiveIntegerField(default=0)
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "model_metrics"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.model_name} @ {self.created_at:%Y-%m-%d %H:%M}"


class LLMCallLog(models.Model):
    """One row per LLM API call: used for the latency and cost numbers on the metrics page."""

    purpose = models.CharField(max_length=30)  # "intake", "chat", "rag", "evaluation"
    provider = models.CharField(max_length=20)
    model = models.CharField(max_length=60)
    success = models.BooleanField(default=True)
    latency_ms = models.PositiveIntegerField(default=0)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    error = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "llm_calls"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.purpose} {self.model} {self.latency_ms}ms"
