from rest_framework import serializers

from ..models.ccf import CCFUpload


class CCFUploadSerializer(serializers.ModelSerializer):
    """Read serializer for CCF upload audit records."""

    class Meta:
        model = CCFUpload
        fields = [
            "id",
            "uploaded_at",
            "total_records",
            "new_count",
            "updated_count",
            "unchanged_count",
            "error_count",
            "error_details",
        ]
        read_only_fields = fields


class CCFFileUploadSerializer(serializers.Serializer):
    """
    Accepts either a multipart file upload (JSON file) or a raw JSON body.
    The view checks both and parses accordingly.
    """

    file = serializers.FileField(required=False)
    records = serializers.ListField(
        child=serializers.DictField(),
        required=False,
    )

    def validate(self, attrs):
        if not attrs.get("file") and not attrs.get("records"):
            raise serializers.ValidationError(
                "Provide either a 'file' (multipart) or a 'records' JSON body."
            )
        return attrs
