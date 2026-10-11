from django.contrib import admin

from .models import ChatHistory, Document, LLMCallLog, ModelMetric


@admin.register(ModelMetric)
class ModelMetricAdmin(admin.ModelAdmin):
    list_display = ("model_name", "n_train", "n_test", "created_at")
    list_filter = ("model_name",)


@admin.register(LLMCallLog)
class LLMCallLogAdmin(admin.ModelAdmin):
    list_display = ("purpose", "model", "success", "latency_ms", "input_tokens", "output_tokens", "cost_usd", "created_at")
    list_filter = ("purpose", "success", "model")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "file_name", "pages", "uploaded_by", "created_at")


@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "session_id", "role", "tool_name", "refused", "created_at")
    list_filter = ("role", "refused")
    search_fields = ("content", "session_id")
