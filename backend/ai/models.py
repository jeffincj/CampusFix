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
