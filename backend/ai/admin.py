from django.contrib import admin

from .models import ModelMetric


@admin.register(ModelMetric)
class ModelMetricAdmin(admin.ModelAdmin):
    list_display = ("model_name", "n_train", "n_test", "created_at")
    list_filter = ("model_name",)
