import time
import logging

from django.utils import timezone
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models.carrier import Carrier, ScoreHistory
from ..serializers.carrier import (
    CarrierListSerializer,
    CarrierDetailSerializer,
    ScoreHistorySerializer,
)

logger = logging.getLogger(__name__)

_START_TIME = time.time()


class HealthCheckView(APIView):
    """
    GET /api/health/
    Simple liveness probe used by Docker health checks and CI smoke tests.
    """

    def get(self, request: Request) -> Response:
        return Response(
            {
                "status": "ok",
                "uptime": round(time.time() - _START_TIME, 2),
                "timestamp": timezone.now().isoformat(),
            }
        )


# --- AI-ASSISTED ---
# Tool: Claude Sonnet 4.6
# Prompt: "Create a DRF ModelViewSet for Carrier with list/retrieve only,
#          score filtering via query params, and a nested history action."
# Modifications: Added score_label to queryset annotation, split list/detail
#                serializers, added pagination bypass for small result sets,
#                added custom ordering, improved filter validation.
# --- END AI-ASSISTED ---
class CarrierViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for carrier read operations.

    list   → GET /api/carriers/
    retrieve → GET /api/carriers/{id}/
    history  → GET /api/carriers/{id}/history/

    Query params for list:
        ?limit=N        Return only the first N records (applied after DB sort).
        ?min_score=N    Filter carriers with score >= N.
        ?authority_status=Active|Inactive|Revoked
    """

    queryset = Carrier.objects.all().order_by("-score")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CarrierDetailSerializer
        return CarrierListSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        min_score = self.request.query_params.get("min_score")
        if min_score is not None:
            try:
                qs = qs.filter(score__gte=float(min_score))
            except ValueError:
                logger.warning("Invalid min_score param: %s", min_score)

        authority_status = self.request.query_params.get("authority_status")
        if authority_status:
            qs = qs.filter(authority_status=authority_status)

        limit = self.request.query_params.get("limit")
        if limit is not None:
            try:
                qs = qs[: int(limit)]
            except (ValueError, TypeError):
                logger.warning("Invalid limit param: %s", limit)

        return qs

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request: Request, pk=None) -> Response:
        """
        GET /api/carriers/{id}/history/
        Returns the full score history for a carrier, newest first.
        """
        carrier = self.get_object()
        history_qs = ScoreHistory.objects.filter(carrier=carrier).order_by("-computed_at")
        serializer = ScoreHistorySerializer(history_qs, many=True)
        return Response(
            {
                "carrier_id": carrier.carrier_id,
                "legal_name": carrier.legal_name,
                "history": serializer.data,
            }
        )

    def list(self, request: Request, *args, **kwargs) -> Response:
        """
        Overridden to inject aggregate stats into the response envelope.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        total = Carrier.objects.count()
        at_risk = Carrier.objects.filter(score__lt=40).count()

        return Response(
            {
                "total": total,
                "at_risk_count": at_risk,
                "results": serializer.data,
            }
        )
