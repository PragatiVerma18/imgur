from ulid2 import generate_ulid_as_uuid

from django.db import models
from django.utils import timezone


class UUIDAsPrimaryKey(models.Model):
    id = models.UUIDField(
        primary_key=True, default=generate_ulid_as_uuid, editable=False
    )

    class Meta:
        abstract = True


class AuditDates(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.now()
        super().save(*args, **kwargs)

    def save_fields(self, fields):
        self.updated_at = timezone.now()
        if "updated_at" not in fields:
            fields = list(fields) + ["updated_at"]
        self.save(update_fields=fields)


class ProcessingJob(AuditDates, UUIDAsPrimaryKey):
    STATUS_PENDING = "PENDING"
    STATUS_PROCESSING = "PROCESSING"
    STATUS_COMPLETED = "COMPLETED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    webhook_url = models.URLField(null=True, blank=True)


class Image(AuditDates, UUIDAsPrimaryKey):
    STATUS_PENDING = "PENDING"
    STATUS_PROCESSED = "PROCESSED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSED, "Processed"),
    ]

    job = models.ForeignKey(
        ProcessingJob, on_delete=models.CASCADE, related_name="images", db_index=True
    )
    product_name = models.CharField(max_length=255, default="")
    input_url = models.URLField()
    output_url = models.URLField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
