"""
CCF Processing Service
========================
Orchestrates the full pipeline for a CCF file upload:

1. Validate each carrier record (schema + types).
2. Compute SHA-256 hash for change detection.
3. Compare against stored hash → skip if unchanged.
4. Score changed/new records.
5. Persist to DB and append to score history.
6. Return a processing summary.

Architecture note:
The service is a plain Python class with no Django import dependencies
in its core logic, making it straightforward to unit-test without a
running database. DB operations are injected via the repository pattern
(thin functions at the bottom of this module).
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from src.scoring.models.carrier import Carrier
from src.scoring.services.scoring import compute_score
from src.scoring.serializers.carrier import CCFCarrierInputSerializer
from src.scoring.utils.hashing import compute_record_hash, detect_change
from src.scoring.models import CCFUpload 

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Summary returned to the API caller after a CCF upload."""

    total_records: int = 0
    new_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    error_count: int = 0
    errors: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_records": self.total_records,
            "new_count": self.new_count,
            "updated_count": self.updated_count,
            "unchanged_count": self.unchanged_count,
            "error_count": self.error_count,
            "errors": self.errors,
        }


# --- AI-ASSISTED ---
# Tool: Claude Sonnet 4.6
# Prompt: "Write a Python service class that processes a list of CCF carrier
#          dicts: validate, hash, detect changes, score, and upsert to DB."
# Modifications: Decoupled DB calls into separate functions for testability,
#                added per-record error isolation (one bad record doesn't abort
#                the batch), added ScoreHistory append, added CCFUpload audit log.
# --- END AI-ASSISTED ---
class CCFProcessingService:
    """
    Stateless service class for processing CCF uploads.
    Instantiate once per request.
    """

    def process(self, records: list[dict[str, Any]]) -> ProcessingResult:
        """
        Main entry point. Processes a list of raw CCF record dicts.

        Args:
            records: List of dicts parsed from the uploaded JSON file.

        Returns:
            ProcessingResult with counts and any per-record errors.
        """
        result = ProcessingResult(total_records=len(records))

        # Pre-fetch all existing hashes in one DB query (avoids N+1)
        existing_carriers = {
            c.carrier_id: c
            for c in Carrier.objects.filter(
                carrier_id__in=[r.get("carrier_id") for r in records if isinstance(r, dict)]
            )
        }

        for raw_record in records:
            try:
                status = self._process_single(raw_record, existing_carriers)
                if status == "new":
                    result.new_count += 1
                elif status == "updated":
                    result.updated_count += 1
                else:
                    result.unchanged_count += 1
            except Exception as exc:  # noqa: BLE001
                carrier_id = raw_record.get("carrier_id", "unknown") if isinstance(raw_record, dict) else "unknown"
                logger.error("Error processing carrier_id=%s: %s", carrier_id, exc)
                result.error_count += 1
                result.errors.append({"carrier_id": carrier_id, "error": str(exc)})

        # Persist audit log
        _save_upload_audit(result)

        logger.info(
            "CCF processing complete: total=%d new=%d updated=%d unchanged=%d errors=%d",
            result.total_records,
            result.new_count,
            result.updated_count,
            result.unchanged_count,
            result.error_count,
        )
        return result

    def _process_single(
        self,
        raw_record: dict,
        existing_carriers: dict[str, Carrier],
    ) -> str:
        """
        Processes a single carrier record.

        Returns:
            "new" | "updated" | "unchanged"
        """
        # 1. Validate
        serializer = CCFCarrierInputSerializer(data=raw_record)
        if not serializer.is_valid():
            raise ValueError(f"Validation failed: {serializer.errors}")

        validated = serializer.validated_data

        # 2. Hash
        incoming_hash = compute_record_hash(raw_record)

        # 3. Change detection
        carrier_id = validated["carrier_id"]
        existing = existing_carriers.get(carrier_id)
        stored_hash = existing.record_hash if existing else None
        changed, reason = detect_change(incoming_hash, stored_hash)

        if not changed:
            logger.debug("Skipping unchanged carrier_id=%s", carrier_id)
            return "unchanged"

        # 4. Score
        breakdown = compute_score(validated)

        # 5. Upsert
        is_new = _upsert_carrier(validated, breakdown, incoming_hash, existing)

        # 6. Append history
        carrier_obj = Carrier.objects.get(carrier_id=carrier_id)
        _append_score_history(carrier_obj, breakdown)

        return "new" if is_new else "updated"


# ---------------------------------------------------------------------------
# Repository helpers – thin DB wrappers; easy to mock in tests
# ---------------------------------------------------------------------------

def _upsert_carrier(
    validated: dict,
    breakdown,
    record_hash: str,
    existing: Carrier | None,
) -> bool:
    """
    Creates or updates a Carrier record.
    Returns True if this was a new creation.
    """
    defaults = {
        "dot_number": validated["dot_number"],
        "legal_name": validated["legal_name"],
        "safety_rating": validated["safety_rating"],
        "out_of_service_pct": validated["out_of_service_pct"],
        "crash_total": validated["crash_total"],
        "driver_oos_pct": validated["driver_oos_pct"],
        "insurance_on_file": validated["insurance_on_file"],
        "authority_status": validated["authority_status"],
        "last_inspection_date": str(validated["last_inspection_date"]),
        "fleet_size": validated.get("fleet_size", 1),
        "score": breakdown.total,
        "score_breakdown": breakdown.to_dict(),
        "record_hash": record_hash,
    }
    _, created = Carrier.objects.update_or_create(
        carrier_id=validated["carrier_id"],
        defaults=defaults,
    )
    return created


def _append_score_history(carrier: Carrier, breakdown) -> None:
    """Appends a ScoreHistory entry for a carrier."""
    ScoreHistory.objects.create(
        carrier=carrier,
        score=breakdown.total,
        score_breakdown=breakdown.to_dict(),
    )


def _save_upload_audit(result: ProcessingResult) -> None:
    """Persists a CCFUpload audit record."""
    CCFUpload.objects.create(
        total_records=result.total_records,
        new_count=result.new_count,
        updated_count=result.updated_count,
        unchanged_count=result.unchanged_count,
        error_count=result.error_count,
        error_details=result.errors,
    )
