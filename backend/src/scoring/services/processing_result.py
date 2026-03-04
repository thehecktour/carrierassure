# --- AI-ASSISTED ---
# Tool: Claude Sonnet 4.6
# Prompt: "Extract the ProcessingResult dataclass from a monolithic service
#          into its own module following Single Responsibility Principle."
# Modifications: Added register_new, register_updated, register_unchanged,
#                and register_error methods to encapsulate counter mutation
#                logic, avoiding raw increments scattered across the service.
# --- END AI-ASSISTED ---

"""
ProcessingResult Value Object
==============================
Single Responsibility: pure data container for the CCF processing summary.
No logic, no DB access, no validation — just data and serialization.
"""

from dataclasses import dataclass, field


@dataclass
class ProcessingResult:
    """Immutable summary returned to the API caller after a CCF upload."""

    total_records: int = 0
    new_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    error_count: int = 0
    errors: list = field(default_factory=list)

    def register_new(self) -> None:
        self.new_count += 1

    def register_updated(self) -> None:
        self.updated_count += 1

    def register_unchanged(self) -> None:
        self.unchanged_count += 1

    def register_error(self, carrier_id: str, error: str) -> None:
        self.error_count += 1
        self.errors.append({"carrier_id": carrier_id, "error": error})

    def to_dict(self) -> dict:
        return {
            "total_records": self.total_records,
            "new_count": self.new_count,
            "updated_count": self.updated_count,
            "unchanged_count": self.unchanged_count,
            "error_count": self.error_count,
            "errors": self.errors,
        }
