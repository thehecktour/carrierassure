from django.db import models
from django.utils import timezone

class SafetyRating(models.TextChoices):
    SATISFACTORY = "Satisfactory", "Satisfactory"
    CONDITIONAL = "Conditional", "Conditional"
    UNSATISFACTORY = "Unsatisfactory", "Unsatisfactory"


class AuthorityStatus(models.TextChoices):
    ACTIVE = "Active", "Active"
    INACTIVE = "Inactive", "Inactive"
    REVOKED = "Revoked", "Revoked"


class Carrier(models.Model):
    """
    Persisted carrier record with current score and hash for change detection.
    The record_hash field is the SHA-256 of the canonical CCF input JSON,
    used to skip re-processing on identical re-uploads.
    """

    # Identity
    carrier_id = models.CharField(max_length=64, unique=True, db_index=True)
    dot_number = models.CharField(max_length=32, db_index=True)
    legal_name = models.CharField(max_length=255)

    # CCF Fields
    safety_rating = models.CharField(
        max_length=20,
        choices=SafetyRating.choices,
    )
    out_of_service_pct = models.FloatField()
    crash_total = models.IntegerField()
    driver_oos_pct = models.FloatField()
    insurance_on_file = models.BooleanField()
    authority_status = models.CharField(
        max_length=20,
        choices=AuthorityStatus.choices,
    )
    last_inspection_date = models.DateField()
    fleet_size = models.IntegerField(default=1)

    # Scoring
    score = models.FloatField(default=0.0, db_index=True)
    score_breakdown = models.JSONField(default=dict)

    # Change detection
    record_hash = models.CharField(max_length=64)

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-score"]
        indexes = [
            models.Index(fields=["-score"]),
            models.Index(fields=["authority_status"]),
        ]

    def __str__(self):
        return f"{self.legal_name} ({self.carrier_id}) – Score: {self.score:.1f}"


class ScoreHistory(models.Model):
    """
    Append-only log of every score computation for a carrier.
    Enables the Advanced Analytics history panel on the frontend.
    """
    carrier = models.ForeignKey(
        Carrier,
        on_delete=models.CASCADE,
        related_name="score_history",
    )
    score = models.FloatField()
    score_breakdown = models.JSONField(default=dict)
    computed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-computed_at"]

    def __str__(self):
        return f"{self.carrier.carrier_id} – {self.score:.1f} @ {self.computed_at}"
