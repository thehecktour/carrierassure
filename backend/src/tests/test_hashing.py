"""
Tests for src/scoring/utils/hashing.py

Cobre:
- compute_record_hash: determinismo, JSON canônico, whitelist de campos,
  inputs inválidos, robustez a valores None
- detect_change: novo registro, inalterado, modificado, tipos de retorno
"""

import pytest

from src.scoring.utils.hashing import _HASH_FIELDS, compute_record_hash, detect_change


def make_record(**overrides) -> dict:
    base = {
        "carrier_id": "MC-123456",
        "dot_number": "1234567",
        "legal_name": "Reliable Freight LLC",
        "safety_rating": "Satisfactory",
        "out_of_service_pct": 12.5,
        "crash_total": 2,
        "driver_oos_pct": 5.3,
        "insurance_on_file": True,
        "authority_status": "Active",
        "last_inspection_date": "2025-11-15",
        "fleet_size": 45,
    }
    base.update(overrides)
    return base

class TestComputeRecordHashFormat:
    def test_returns_string(self):
        assert isinstance(compute_record_hash(make_record()), str)

    def test_returns_64_chars(self):
        assert len(compute_record_hash(make_record())) == 64

    def test_returns_lowercase_hex(self):
        result = compute_record_hash(make_record())
        assert all(c in "0123456789abcdef" for c in result)


class TestComputeRecordHashDeterminism:
    def test_same_record_same_hash(self):
        r = make_record()
        assert compute_record_hash(r) == compute_record_hash(r)

    def test_identical_records_same_hash(self):
        assert compute_record_hash(make_record()) == compute_record_hash(make_record())

    def test_different_carrier_id_different_hash(self):
        r1 = make_record(carrier_id="MC-AAA")
        r2 = make_record(carrier_id="MC-BBB")
        assert compute_record_hash(r1) != compute_record_hash(r2)

    def test_key_insertion_order_does_not_affect_hash(self):
        """Canonical JSON deve garantir que ordem de inserção não importa."""
        r1 = {
            "carrier_id": "MC-X", "dot_number": "1234567", "legal_name": "X",
            "safety_rating": "Satisfactory", "out_of_service_pct": 10.0,
            "crash_total": 1, "driver_oos_pct": 5.0, "insurance_on_file": True,
            "authority_status": "Active", "last_inspection_date": "2025-01-01",
            "fleet_size": 10,
        }
        r2 = {k: r1[k] for k in reversed(list(r1.keys()))}
        assert compute_record_hash(r1) == compute_record_hash(r2)

    def test_hash_is_stable_across_multiple_calls(self):
        r = make_record()
        hashes = {compute_record_hash(r) for _ in range(10)}
        assert len(hashes) == 1


class TestComputeRecordHashFieldWhitelist:
    def test_computed_fields_do_not_affect_hash(self):
        """score, created_at e outros campos computados não devem mudar o hash."""
        r1 = make_record()
        r2 = make_record()
        r2["score"] = 99.9
        r2["created_at"] = "2099-01-01T00:00:00Z"
        r2["record_hash"] = "qualquercoisa"
        assert compute_record_hash(r1) == compute_record_hash(r2)

    def test_each_hash_field_affects_hash(self):
        """Qualquer mudança em campo CCF deve gerar hash diferente."""
        base_hash = compute_record_hash(make_record())
        mutations = {
            "safety_rating": "Unsatisfactory",
            "out_of_service_pct": 99.9,
            "crash_total": 9,
            "driver_oos_pct": 88.0,
            "insurance_on_file": False,
            "authority_status": "Revoked",
            "fleet_size": 999,
            "legal_name": "Nome Diferente LLC",
            "dot_number": "9999999",
            "last_inspection_date": "2020-01-01",
        }
        for field, value in mutations.items():
            modified_hash = compute_record_hash(make_record(**{field: value}))
            assert modified_hash != base_hash, (
                f"Hash deveria mudar quando {field}={value!r}"
            )

    def test_all_hash_fields_are_present_in_whitelist(self):
        """Garante que nenhum campo CCF foi esquecido da whitelist."""
        expected = {
            "carrier_id", "dot_number", "legal_name", "safety_rating",
            "out_of_service_pct", "crash_total", "driver_oos_pct",
            "insurance_on_file", "authority_status", "last_inspection_date",
            "fleet_size",
        }
        assert set(_HASH_FIELDS) == expected

    def test_missing_optional_field_produces_consistent_hash(self):
        """Campo ausente vira None no canonical dict — deve ser estável."""
        r1 = make_record()
        del r1["fleet_size"]
        r2 = make_record()
        del r2["fleet_size"]
        assert compute_record_hash(r1) == compute_record_hash(r2)

    def test_none_value_differs_from_actual_value(self):
        """None e um valor real devem produzir hashes diferentes."""
        r_with_value = make_record(fleet_size=10)
        r_with_none = make_record()
        r_with_none["fleet_size"] = None
        assert compute_record_hash(r_with_value) != compute_record_hash(r_with_none)


class TestComputeRecordHashInvalidInputs:
    def test_raises_on_none(self):
        with pytest.raises(ValueError, match="must be a dict"):
            compute_record_hash(None)

    def test_raises_on_string(self):
        with pytest.raises(ValueError, match="must be a dict"):
            compute_record_hash("not a dict")

    def test_raises_on_list(self):
        with pytest.raises(ValueError, match="must be a dict"):
            compute_record_hash([{"carrier_id": "MC-X"}])

    def test_raises_on_int(self):
        with pytest.raises(ValueError):
            compute_record_hash(42)

    def test_empty_dict_returns_valid_hash(self):
        """Dict vazio é válido — todos os campos ficam None no canonical."""
        result = compute_record_hash({})
        assert isinstance(result, str)
        assert len(result) == 64

    def test_handles_none_field_values(self):
        """Campos com valor None não devem explodir."""
        r = make_record(fleet_size=None, crash_total=None)
        result = compute_record_hash(r)
        assert isinstance(result, str)
        assert len(result) == 64

class TestDetectChange:
    def test_none_stored_hash_means_new_record(self):
        changed, reason = detect_change("abc123", None)
        assert changed is True
        assert reason == "new_record"

    def test_same_hash_means_unchanged(self):
        h = "a" * 64
        changed, reason = detect_change(h, h)
        assert changed is False
        assert reason == "unchanged"

    def test_different_hash_means_changed(self):
        changed, reason = detect_change("a" * 64, "b" * 64)
        assert changed is True
        assert reason == "hash_mismatch"

    def test_partial_match_is_still_changed(self):
        h = "a" * 64
        partial = h[:32] + "b" * 32
        changed, reason = detect_change(partial, h)
        assert changed is True
        assert reason == "hash_mismatch"

    def test_returns_tuple_of_two(self):
        result = detect_change("x", None)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_changed_is_bool(self):
        changed, _ = detect_change("x", "y")
        assert isinstance(changed, bool)

    def test_reason_is_str(self):
        _, reason = detect_change("x", None)
        assert isinstance(reason, str)

    def test_empty_string_stored_hash_triggers_mismatch(self):
        changed, reason = detect_change("abc", "")
        assert changed is True
        assert reason == "hash_mismatch"

    def test_real_hashes_from_identical_records_are_unchanged(self):
        """Integração: dois records idênticos devem resultar em unchanged."""
        r = make_record()
        h1 = compute_record_hash(r)
        h2 = compute_record_hash(r)
        changed, reason = detect_change(h1, h2)
        assert changed is False
        assert reason == "unchanged"

    def test_real_hashes_from_different_records_trigger_mismatch(self):
        """Integração: records diferentes devem resultar em hash_mismatch."""
        h1 = compute_record_hash(make_record(crash_total=0))
        h2 = compute_record_hash(make_record(crash_total=9))
        changed, reason = detect_change(h1, h2)
        assert changed is True
        assert reason == "hash_mismatch"
