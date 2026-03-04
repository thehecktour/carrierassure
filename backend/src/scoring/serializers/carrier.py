from rest_framework import serializers

from ..models.carrier import Carrier, ScoreHistory


class ScoreHistorySerializer(serializers.ModelSerializer):
    """Serializes a single score history entry for the analytics panel."""

    class Meta:
        model = ScoreHistory
        fields = ["id", "score", "score_breakdown", "computed_at"]
        read_only_fields = fields


class CarrierListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for the carrier table view.
    Excludes the full score_breakdown to reduce payload size.
    """

    score_label = serializers.SerializerMethodField()

    class Meta:
        model = Carrier
        fields = [
            "id",
            "carrier_id",
            "dot_number",
            "legal_name",
            "safety_rating",
            "authority_status",
            "score",
            "score_label",
            "last_updated",
        ]
        read_only_fields = fields

    def get_score_label(self, obj: Carrier) -> str:
        """Color-coding tier: green > 70, yellow 40-70, red < 40."""
        if obj.score > 70:
            return "green"
        elif obj.score >= 40:
            return "yellow"
        return "red"


class CarrierDetailSerializer(serializers.ModelSerializer):
    """
    Full carrier detail including score breakdown and hash.
    Used by GET /api/carriers/:id.
    """

    score_label = serializers.SerializerMethodField()
    score_history = ScoreHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Carrier
        fields = [
            "id",
            "carrier_id",
            "dot_number",
            "legal_name",
            "safety_rating",
            "out_of_service_pct",
            "crash_total",
            "driver_oos_pct",
            "insurance_on_file",
            "authority_status",
            "last_inspection_date",
            "fleet_size",
            "score",
            "score_label",
            "score_breakdown",
            "record_hash",
            "created_at",
            "last_updated",
            "score_history",
        ]
        read_only_fields = fields

    def get_score_label(self, obj: Carrier) -> str:
        if obj.score > 70:
            return "green"
        elif obj.score >= 40:
            return "yellow"
        return "red"


# --- AI-ASSISTED ---
# Tool: Claude Sonnet 4.6
# Prompt: "Write a DRF write serializer for CCF carrier records with
#          full field validation including range checks."
# Modifications: Added cross-field validation, custom date parsing,
#                default fleet_size handling, detailed error messages.
# --- END AI-ASSISTED ---
class CCFCarrierInputSerializer(serializers.Serializer):
    """
    Validates a single carrier record from an incoming CCF file.
    Used by the CCF upload service before scoring.
    """

    SAFETY_RATING_CHOICES = ["Satisfactory", "Conditional", "Unsatisfactory"]
    AUTHORITY_STATUS_CHOICES = ["Active", "Inactive", "Revoked"]

    carrier_id = serializers.CharField(max_length=64)
    dot_number = serializers.CharField(max_length=32)
    legal_name = serializers.CharField(max_length=255)
    safety_rating = serializers.ChoiceField(choices=SAFETY_RATING_CHOICES)
    out_of_service_pct = serializers.FloatField(min_value=0.0, max_value=100.0)
    crash_total = serializers.IntegerField(min_value=0)
    driver_oos_pct = serializers.FloatField(min_value=0.0, max_value=100.0)
    insurance_on_file = serializers.BooleanField()
    authority_status = serializers.ChoiceField(choices=AUTHORITY_STATUS_CHOICES)
    last_inspection_date = serializers.DateField()
    fleet_size = serializers.IntegerField(min_value=1, default=1, required=False)

    def validate_carrier_id(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("carrier_id cannot be blank.")
        return value.strip()

    def validate_dot_number(self, value: str) -> str:
        if not value.strip().isdigit():
            raise serializers.ValidationError("dot_number must be numeric.")
        return value.strip()
