from django.db import models
from django.utils import timezone


class CCFUpload(models.Model):
    """
    Audit log of every CCF file upload.
    Stores processing summary for debugging and analytics.
    """
    uploaded_at = models.DateTimeField(default=timezone.now, db_index=True)
    total_records = models.IntegerField(default=0)
    new_count = models.IntegerField(default=0)
    updated_count = models.IntegerField(default=0)
    unchanged_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    error_details = models.JSONField(default=list)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return (
            f"CCFUpload @ {self.uploaded_at} "
            f"(new={self.new_count}, updated={self.updated_count}, "
            f"unchanged={self.unchanged_count})"
        )
