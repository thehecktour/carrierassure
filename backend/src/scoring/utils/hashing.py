"""
Hash-Based Change Detection Service
=====================================
Core production pattern: each carrier record is hashed (SHA-256 over
canonical JSON) before persisting. On re-upload, we compare incoming
hashes against stored hashes and only re-score changed records.

Why canonical JSON?
- Key order in Python dicts is insertion-order (Python 3.7+) but CCF
  producers may sort keys differently. Sorting keys guarantees the same
  byte sequence → same hash for semantically identical records.
- We exclude keys whose absence should not trigger re-scoring (none in
  this schema, but the pattern is extensible).
"""

import hashlib
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Fields that are hashed. We hash ALL CCF input fields to detect any change.
_HASH_FIELDS = [
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
]


# --- AI-ASSISTED ---
# Tool: Claude Sonnet 4.6
# Prompt: "Generate a SHA-256 hashing function that takes a carrier record
#          object, extracts only the CCF input fields, sorts keys
#          alphabetically, and returns a hex digest."
# Modifications: Added explicit field whitelist (_HASH_FIELDS) instead of
#                hashing the whole dict to avoid hashing computed fields
#                (score, created_at) which would create false positives.
#                Added null-safe serialization and TypeError handling.
# --- END AI-ASSISTED ---
def compute_record_hash(carrier_data: dict) -> str:
    """
    Computes a deterministic SHA-256 hash for a carrier record.

    Only CCF input fields are included. The dict is serialized to
    canonical JSON (sorted keys, no whitespace) before hashing.

    Args:
        carrier_data: dict containing CCF fields.

    Returns:
        64-character lowercase hex string (SHA-256 digest).

    Raises:
        ValueError: if carrier_data is None or not a dict.
    """
    if not isinstance(carrier_data, dict):
        raise ValueError(f"carrier_data must be a dict, got {type(carrier_data)}")

    canonical = {k: carrier_data.get(k) for k in sorted(_HASH_FIELDS)}

    try:
        serialized = json.dumps(canonical, sort_keys=True, default=str)
    except TypeError as exc:
        raise ValueError(f"Failed to serialize carrier record for hashing: {exc}") from exc

    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    logger.debug(
        "Hashed carrier_id=%s → %s", carrier_data.get("carrier_id", "?"), digest[:8] + "..."
    )
    return digest


def detect_change(
    incoming_hash: str,
    stored_hash: Optional[str],
) -> tuple[bool, str]:
    """
    Compares the incoming record hash against the stored hash.

    Args:
        incoming_hash: SHA-256 of the incoming CCF record.
        stored_hash:   SHA-256 stored in the DB for this carrier_id,
                       or None if this is a new carrier.

    Returns:
        (changed: bool, reason: str)
        changed = True  → record must be re-processed.
        changed = False → record is identical; skip re-scoring.
    """
    if stored_hash is None:
        return True, "new_record"
    if incoming_hash != stored_hash:
        return True, "hash_mismatch"
    return False, "unchanged"
