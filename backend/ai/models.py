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


class Document(models.Model):
    """A college rules PDF uploaded by an admin, used by the chat assistant (RAG)."""

    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="documents/")
    file_name = models.CharField(max_length=200)  # original name, shown as the source
    pages = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documents"
        ordering = ["title"]

    def __str__(self):
        return self.title


class DocumentChunk(models.Model):
    """A piece of a document (about one paragraph) with its embedding."""

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    page = models.PositiveIntegerField()  # 1-based page number, shown as the source
    chunk_index = models.PositiveIntegerField()
    text = models.TextField()
    embedding = models.BinaryField()
    embedding_model = models.CharField(max_length=80)

    class Meta:
        db_table = "document_chunks"
        ordering = ["document_id", "chunk_index"]


class ChatHistory(models.Model):
    """Every message of every chat conversation (user question, tool call, assistant answer)."""

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        TOOL = "tool", "Tool call"

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="chat_messages")
    session_id = models.CharField(max_length=40, db_index=True)  # groups the messages of one conversation
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    tool_name = models.CharField(max_length=50, blank=True)
    sources = models.JSONField(default=list, blank=True)  # [{"file": ..., "page": ...}]
    refused = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_history"
        ordering = ["created_at", "id"]
