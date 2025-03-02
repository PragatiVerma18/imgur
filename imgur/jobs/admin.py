from django.contrib import admin
from .models import ProcessingJob, Image


@admin.register(ProcessingJob)
class ProcessingJobAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "created_at", "updated_at")
    search_fields = ("id",)
    list_filter = ("status",)
    ordering = ("-created_at",)


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = (
        "job",
        "input_url",
        "output_url",
        "status",
        "created_at",
        "updated_at",
    )
    search_fields = ("id", "job__id", "input_url", "output_url")
    list_filter = ("status",)
    ordering = ("-created_at",)
