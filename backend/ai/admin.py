from django.contrib import admin

from .models import LLMCallLog, ModelMetric


@admin.register(ModelMetric)
class ModelMetricAdmin(admin.ModelAdmin):
    list_display = ("model_name", "n_train", "n_test", "created_at")
    list_filter = ("model_name",)


@admin.register(LLMCallLog)
class LLMCallLogAdmin(admin.ModelAdmin):
    list_display = ("purpose", "model", "success", "latency_ms", "input_tokens", "output_tokens", "cost_usd", "created_at")
    list_filter = ("purpose", "success", "model")
