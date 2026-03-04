import json
import logging

from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.request import Request
from rest_framework.response import Response

from ..models.ccf import CCFUpload
from ..serializers.ccf import CCFUploadSerializer
from ..services.processing_result import CCFProcessingService

logger = logging.getLogger(__name__)


class CCFUploadViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for CCF upload operations.

    list     → GET  /api/ccf/uploads/          (audit log)
    retrieve → GET  /api/ccf/uploads/{id}/
    upload   → POST /api/ccf/upload/            (main upload action)
    """

    queryset = CCFUpload.objects.all().order_by("-uploaded_at")
    serializer_class = CCFUploadSerializer
    parser_classes = [MultiPartParser, JSONParser]

    @action(
        detail=False,
        methods=["post"],
        url_path="upload",
        parser_classes=[MultiPartParser, JSONParser],
    )
    def upload(self, request: Request) -> Response:
        """
        POST /api/ccf/upload/

        Accepts:
          - multipart/form-data with a 'file' field (JSON file)
          - application/json body: {"records": [...]}

        Returns processing summary with new/updated/unchanged counts.
        """
        records = self._extract_records(request)
        if records is None:
            return Response(
                {"error": "No valid CCF data found. Provide a JSON file or records body."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(records, list):
            return Response(
                {"error": "CCF payload must be a JSON array of carrier records."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(records) == 0:
            return Response(
                {"error": "CCF file is empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = CCFProcessingService()
        result = service.process(records)

        http_status = (
            status.HTTP_207_MULTI_STATUS if result.error_count > 0 else status.HTTP_200_OK
        )
        return Response(result.to_dict(), status=http_status)

    def _extract_records(self, request: Request):
        """
        Extracts the list of carrier records from either:
        - A multipart file upload (JSON file)
        - A raw JSON body with a 'records' key
        - A raw JSON body that is itself a list
        """
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            try:
                content = uploaded_file.read().decode("utf-8")
                return json.loads(content)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                logger.warning("Failed to parse uploaded CCF file: %s", exc)
                return None

        body = request.data
        if isinstance(body, dict) and "records" in body:
            return body["records"]

        if isinstance(body, list):
            return body

        return None
