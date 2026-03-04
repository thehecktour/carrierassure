"""
RecordProcessor
================
Single Responsibility: processes ONE carrier record through the full pipeline.

Pipeline:
  validate → hash → detect change → score → persist

This class knows nothing about batches, HTTP, or audit logs.
It receives its dependencies via constructor injection (DIP),
making it fully testable without a running database.
"""

import logging
from typing import Literal

from src.scoring.models import Carrier
from src.scoring.serializers.carrier import CCFCarrierInputSerializer
from src.scoring.services.scoring import compute_score
from src.scoring.utils.hashing import compute_record_hash, detect_change

logger = logging.getLogger(__name__)

RecordStatus = Literal["new", "updated", "unchanged"]


class RecordProcessor:
    """
    Processes a single CCF carrier record.

    Dependencies are injected — this class never instantiates
    its own DB access or hashing logic.
    """

    def __init__(self, repository):
        """
        Args:
            repository: ICarrierRepository implementation.
        """
        self._repository = repository

    def process(
        self,
        raw_record: dict,
        existing_carriers: dict[str, Carrier],
    ) -> RecordStatus:
        """
        Runs the full pipeline for one record.

        Args:
            raw_record: Raw dict from the CCF file.
            existing_carriers: Pre-fetched {carrier_id: Carrier} map.

        Returns:
            "new" | "updated" | "unchanged"

        Raises:
            ValueError: if validation fails.
        """
        validated = self._validate(raw_record)
        incoming_hash = compute_record_hash(raw_record)

        carrier_id = validated["carrier_id"]
        existing = existing_carriers.get(carrier_id)
        stored_hash = existing.record_hash if existing else None

        changed, reason = detect_change(incoming_hash, stored_hash)
        if not changed:
            logger.debug("Skipping unchanged carrier_id=%s", carrier_id)
            return "unchanged"

        breakdown = compute_score(validated)
        is_new = self._repository.upsert(validated, breakdown, incoming_hash)
        self._repository.append_score_history(carrier_id, breakdown)

        logger.info(
            "Processed carrier_id=%s status=%s score=%.2f",
            carrier_id,
            "new" if is_new else "updated",
            breakdown.total,
        )
        return "new" if is_new else "updated"

    def _validate(self, raw_record: dict) -> dict:
        """Validates and returns cleaned data. Raises ValueError on failure."""
        serializer = CCFCarrierInputSerializer(data=raw_record)
        if not serializer.is_valid():
            raise ValueError(f"Validation failed: {serializer.errors}")
        return serializer.validated_data
