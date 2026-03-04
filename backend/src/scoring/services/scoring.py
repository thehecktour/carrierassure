"""
Carrier Safety Scoring Service
================================
Computes a composite 0–100 safety score from CCF fields.

Scoring rationale (documented per assessment requirements):
- safety_rating (25%): Regulatory USDOT rating is the strongest signal.
  Satisfactory → full marks; Conditional → half; Unsatisfactory → zero.
- out_of_service_pct (20%): Vehicle OOS rate reflects maintenance standards.
  Linear inverse scale: 0% = 20pts, 100% = 0pts.
- crash_total (20%): Crash history is a lagging but reliable safety indicator.
  Inversely scaled, capped at 10 crashes (beyond which marginal risk is flat).
- driver_oos_pct (15%): Driver compliance failures. Same inverse logic as vehicle OOS.
- insurance_on_file (10%): Binary compliance check. Missing insurance = instant deduction.
- authority_status (10%): Regulatory standing. Revoked carriers should score very low.

Trade-off: A purely additive model is transparent and auditable, but it allows
a carrier to score ~65/100 even with Unsatisfactory safety_rating. In production
we would add multiplier penalties, but for this assessment the additive model is
documented and testable.
"""

import logging
from dataclasses import dataclass, field
from typing import Final

logger = logging.getLogger(__name__)

WEIGHT_SAFETY_RATING: Final[float] = 25.0
WEIGHT_OOS_PCT: Final[float] = 20.0
WEIGHT_CRASH_TOTAL: Final[float] = 20.0
WEIGHT_DRIVER_OOS_PCT: Final[float] = 15.0
WEIGHT_INSURANCE: Final[float] = 10.0
WEIGHT_AUTHORITY_STATUS: Final[float] = 10.0

CRASH_CAP: Final[int] = 10


@dataclass
class ScoreBreakdown:
    """Typed container for per-factor score contributions."""

    safety_rating_score: float = 0.0
    oos_pct_score: float = 0.0
    crash_total_score: float = 0.0
    driver_oos_pct_score: float = 0.0
    insurance_score: float = 0.0
    authority_status_score: float = 0.0
    total: float = field(init=False)

    def __post_init__(self):
        self.total = round(
            self.safety_rating_score
            + self.oos_pct_score
            + self.crash_total_score
            + self.driver_oos_pct_score
            + self.insurance_score
            + self.authority_status_score,
            2,
        )

    def to_dict(self) -> dict:
        return {
            "safety_rating_score": self.safety_rating_score,
            "oos_pct_score": self.oos_pct_score,
            "crash_total_score": self.crash_total_score,
            "driver_oos_pct_score": self.driver_oos_pct_score,
            "insurance_score": self.insurance_score,
            "authority_status_score": self.authority_status_score,
            "total": self.total,
        }


# --- AI-ASSISTED ---
# Tool: Claude Sonnet 4.6
# Prompt: "Write individual pure functions for each scoring factor using
#          weight constants, returning float contributions."
# Modifications: Extracted each factor into its own function for isolated
#                unit testing, added input clamping, added docstrings.
# --- END AI-ASSISTED ---


def score_safety_rating(safety_rating: str) -> float:
    """
    Returns the safety_rating contribution (0–25).
    Satisfactory = 25, Conditional = 12.5, Unsatisfactory = 0.
    """
    mapping = {
        "Satisfactory": WEIGHT_SAFETY_RATING,
        "Conditional": WEIGHT_SAFETY_RATING * 0.5,
        "Unsatisfactory": 0.0,
    }
    result = mapping.get(safety_rating, 0.0)
    logger.debug("safety_rating=%s → %.2f", safety_rating, result)
    return result


def score_out_of_service_pct(pct: float) -> float:
    """
    Returns the vehicle OOS contribution (0–20).
    Linear inverse: lower OOS % → higher score.
    Clamps input to [0, 100].
    """
    pct = max(0.0, min(100.0, pct))
    result = round((1.0 - pct / 100.0) * WEIGHT_OOS_PCT, 4)
    logger.debug("out_of_service_pct=%.2f → %.4f", pct, result)
    return result


def score_crash_total(crashes: int) -> float:
    """
    Returns the crash total contribution (0–20).
    Inversely scaled with a cap at CRASH_CAP (10). Beyond the cap = 0pts.
    Clamps input to [0, ∞].
    """
    crashes = max(0, crashes)
    capped = min(crashes, CRASH_CAP)
    result = round((1.0 - capped / CRASH_CAP) * WEIGHT_CRASH_TOTAL, 4)
    logger.debug("crash_total=%d (capped=%d) → %.4f", crashes, capped, result)
    return result


def score_driver_oos_pct(pct: float) -> float:
    """
    Returns the driver OOS contribution (0–15).
    Linear inverse: lower driver OOS % → higher score.
    Clamps input to [0, 100].
    """
    pct = max(0.0, min(100.0, pct))
    result = round((1.0 - pct / 100.0) * WEIGHT_DRIVER_OOS_PCT, 4)
    logger.debug("driver_oos_pct=%.2f → %.4f", pct, result)
    return result


def score_insurance(insurance_on_file: bool) -> float:
    """Returns the insurance contribution: 10.0 if insured, 0.0 otherwise."""
    result = WEIGHT_INSURANCE if insurance_on_file else 0.0
    logger.debug("insurance_on_file=%s → %.2f", insurance_on_file, result)
    return result


def score_authority_status(status: str) -> float:
    """
    Returns the authority status contribution (0–10).
    Active = 10, Inactive = 5, Revoked = 0.
    """
    mapping = {
        "Active": WEIGHT_AUTHORITY_STATUS,
        "Inactive": WEIGHT_AUTHORITY_STATUS * 0.5,
        "Revoked": 0.0,
    }
    result = mapping.get(status, 0.0)
    logger.debug("authority_status=%s → %.2f", status, result)
    return result


def compute_score(carrier_data: dict) -> ScoreBreakdown:
    """
    Computes the full ScoreBreakdown for a carrier dict from the CCF.

    Args:
        carrier_data: dict with CCF fields (validated before this call).

    Returns:
        ScoreBreakdown with per-factor contributions and total.
    """
    breakdown = ScoreBreakdown(
        safety_rating_score=score_safety_rating(carrier_data.get("safety_rating", "")),
        oos_pct_score=score_out_of_service_pct(carrier_data.get("out_of_service_pct", 100.0)),
        crash_total_score=score_crash_total(carrier_data.get("crash_total", CRASH_CAP)),
        driver_oos_pct_score=score_driver_oos_pct(carrier_data.get("driver_oos_pct", 100.0)),
        insurance_score=score_insurance(carrier_data.get("insurance_on_file", False)),
        authority_status_score=score_authority_status(carrier_data.get("authority_status", "")),
    )
    logger.info(
        "Computed score for carrier_id=%s: %.2f",
        carrier_data.get("carrier_id", "unknown"),
        breakdown.total,
    )
    return breakdown
