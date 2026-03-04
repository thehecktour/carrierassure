"""
CCF Processing Service
========================
Orchestrates the full pipeline for a CCF file upload.

Responsibilities (SRP - each handled by a dedicated class):
  - Validation       -> CCFCarrierInputSerializer
  - Hashing          -> compute_record_hash (hashing.py)
  - Change detection -> detect_change (hashing.py)
  - Scoring          -> compute_score (scoring.py)
  - Persistence      -> ICarrierRepository (repositories.py)
  - Single record    -> RecordProcessor (record_processor.py)
  - Result tracking  -> ProcessingResult (result.py)

This service only orchestrates. It delegates every concern
to a focused collaborator (OCP, SRP, DIP).
"""

import logging
from typing import Any

from src.scoring.repositories.carrier import DjangoCarrierRepository, ICarrierRepository
from src.scoring.services.processing_result import ProcessingResult
from src.scoring.services.record import RecordProcessor

logger = logging.getLogger(__name__)


# --- AI-ASSISTED ---
# Tool: Claude Sonnet 4.6
# Prompt: "Refactor a monolithic CCF processing service into SOLID components
#          using Repository pattern and Dependency Injection."
# Modifications: Extracted RecordProcessor, ProcessingResult, and Repository
#                into separate modules. Service now only orchestrates.
#                Added default DI wiring so the view requires zero changes.
# --- END AI-ASSISTED ---
class CCFProcessingService:
    """
    Stateless orchestrator for CCF file processing.

    Knows ONLY about:
    - Iterating records
    - Delegating to RecordProcessor
    - Collecting results
    - Saving the audit log

    Knows NOTHING about:
    - How hashing works
    - How scoring works
    - How DB access works
    - HTTP / Django internals
    """

    def __init__(
        self,
        repository: ICarrierRepository | None = None,
        record_processor: RecordProcessor | None = None,
    ):
        self._repository = repository or DjangoCarrierRepository()
        self._record_processor = record_processor or RecordProcessor(self._repository)

    def process(self, records: list[dict[str, Any]]) -> ProcessingResult:
        """
        Main entry point. Processes a list of raw CCF record dicts.

        Args:
            records: List of dicts parsed from the uploaded JSON file.

        Returns:
            ProcessingResult with counts and any per-record errors.
        """
        result = ProcessingResult(total_records=len(records))

        # Single DB query to pre-fetch all existing carriers (avoids N+1)
        carrier_ids = [r.get("carrier_id") for r in records if isinstance(r, dict)]
        existing_carriers = self._repository.get_existing_carriers(carrier_ids)

        for raw_record in records:
            self._process_one(raw_record, existing_carriers, result)

        self._save_audit(result)

        logger.info(
            "CCF processing complete: total=%d new=%d updated=%d unchanged=%d errors=%d",
            result.total_records,
            result.new_count,
            result.updated_count,
            result.unchanged_count,
            result.error_count,
        )
        return result

    def _process_one(
        self,
        raw_record: dict,
        existing_carriers: dict,
        result: ProcessingResult,
    ) -> None:
        """Delegates single-record processing and updates the result."""
        carrier_id = (
            raw_record.get("carrier_id", "unknown")
            if isinstance(raw_record, dict)
            else "unknown"
        )
        try:
            status = self._record_processor.process(raw_record, existing_carriers)
            if status == "new":
                result.register_new()
            elif status == "updated":
                result.register_updated()
            else:
                result.register_unchanged()
        except Exception as exc:  # noqa: BLE001
            logger.error("Error processing carrier_id=%s: %s", carrier_id, exc)
            result.register_error(carrier_id, str(exc))

    def _save_audit(self, result: ProcessingResult) -> None:
        self._repository.save_upload_audit(
            total=result.total_records,
            new=result.new_count,
            updated=result.updated_count,
            unchanged=result.unchanged_count,
            errors=result.error_count,
            error_details=result.errors,
        )
