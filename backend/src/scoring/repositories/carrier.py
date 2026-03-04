"""
Repository Pattern for Carrier persistence.
============================================
Follows the Dependency Inversion Principle (DIP):
- High-level service depends on the abstract ICarrierRepository interface,
  not on Django ORM directly.
- Enables easy mocking in unit tests without hitting the database.
"""

from abc import ABC, abstractmethod

from src.scoring.models import Carrier, CCFUpload, ScoreHistory
from src.scoring.services.scoring import ScoreBreakdown


class ICarrierRepository(ABC):
    """Abstract interface for carrier persistence operations."""

    @abstractmethod
    def get_existing_carriers(self, carrier_ids: list[str]) -> dict[str, Carrier]:
        """Fetch carriers by ID in a single query. Returns {carrier_id: Carrier}."""
        raise NotImplementedError

    @abstractmethod
    def upsert(self, validated: dict, breakdown: ScoreBreakdown, record_hash: str) -> bool:
        """
        Creates or updates a Carrier record.
        Returns True if this was a new creation.
        """
        raise NotImplementedError

    @abstractmethod
    def append_score_history(self, carrier_id: str, breakdown: ScoreBreakdown) -> None:
        """Appends a ScoreHistory entry for a carrier."""
        raise NotImplementedError

    @abstractmethod
    def save_upload_audit(
        self,
        total: int,
        new: int,
        updated: int,
        unchanged: int,
        errors: int,
        error_details: list,
    ) -> None:
        """Persists a CCFUpload audit record."""
        raise NotImplementedError


class DjangoCarrierRepository(ICarrierRepository):
    """
    Concrete Django ORM implementation of ICarrierRepository.
    All DB access is isolated here — nowhere else.
    """

    def get_existing_carriers(self, carrier_ids: list[str]) -> dict[str, Carrier]:
        return {
            c.carrier_id: c
            for c in Carrier.objects.filter(carrier_id__in=carrier_ids)
        }

    def upsert(self, validated: dict, breakdown: ScoreBreakdown, record_hash: str) -> bool:
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

    def append_score_history(self, carrier_id: str, breakdown: ScoreBreakdown) -> None:
        carrier = Carrier.objects.get(carrier_id=carrier_id)
        ScoreHistory.objects.create(
            carrier=carrier,
            score=breakdown.total,
            score_breakdown=breakdown.to_dict(),
        )

    def save_upload_audit(
        self,
        total: int,
        new: int,
        updated: int,
        unchanged: int,
        errors: int,
        error_details: list,
    ) -> None:
        CCFUpload.objects.create(
            total_records=total,
            new_count=new,
            updated_count=updated,
            unchanged_count=unchanged,
            error_count=errors,
            error_details=error_details,
        )
