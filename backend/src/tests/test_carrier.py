
import pytest

from src.scoring.models import Carrier, CCFUpload, ScoreHistory
from src.scoring.repositories.carrier import DjangoCarrierRepository, ICarrierRepository
from src.scoring.services.scoring import ScoreBreakdown


def make_breakdown(**overrides) -> ScoreBreakdown:
    """Cria um ScoreBreakdown com valores padrão para testes."""
    defaults = dict(
        safety_rating_score=25.0,
        oos_pct_score=18.0,
        crash_total_score=16.0,
        driver_oos_pct_score=14.0,
        insurance_score=10.0,
        authority_status_score=10.0,
    )
    defaults.update(overrides)
    return ScoreBreakdown(**defaults)


def make_validated(**overrides) -> dict:
    """Retorna um dict validado de carrier para testes."""
    base = {
        "carrier_id": "MC-TEST-001",
        "dot_number": "1234567",
        "legal_name": "Test Carrier LLC",
        "safety_rating": "Satisfactory",
        "out_of_service_pct": 10.0,
        "crash_total": 2,
        "driver_oos_pct": 5.0,
        "insurance_on_file": True,
        "authority_status": "Active",
        "last_inspection_date": "2025-11-15",
        "fleet_size": 10,
    }
    base.update(overrides)
    return base

class TestICarrierRepository:
    def test_cannot_instantiate_abstract_class(self):
        """ICarrierRepository não pode ser instanciada diretamente."""
        with pytest.raises(TypeError):
            ICarrierRepository()

    def test_concrete_class_must_implement_all_methods(self):
        """Classe concreta que não implementa todos os métodos também falha."""
        class Incomplete(ICarrierRepository):
            def get_existing_carriers(self, carrier_ids):
                return {}
            # upsert, append_score_history, save_upload_audit não implementados

        with pytest.raises(TypeError):
            Incomplete()

    def test_concrete_class_with_all_methods_instantiates(self):
        """Classe que implementa todos os métodos pode ser instanciada."""
        class Complete(ICarrierRepository):
            def get_existing_carriers(self, carrier_ids): return {}
            def upsert(self, validated, breakdown, record_hash): return True
            def append_score_history(self, carrier_id, breakdown): pass
            def save_upload_audit(self, total, new, updated, unchanged, errors, error_details): pass

        instance = Complete()
        assert isinstance(instance, ICarrierRepository)

@pytest.mark.django_db
class TestGetExistingCarriers:
    def setup_method(self):
        self.repo = DjangoCarrierRepository()

    def test_returns_empty_dict_when_no_carriers(self):
        result = self.repo.get_existing_carriers(["MC-999"])
        assert result == {}

    def test_returns_dict_keyed_by_carrier_id(self):
        Carrier.objects.create(**make_validated(), score=85.0, score_breakdown={}, record_hash="a" * 64)
        result = self.repo.get_existing_carriers(["MC-TEST-001"])
        assert "MC-TEST-001" in result
        assert isinstance(result["MC-TEST-001"], Carrier)

    def test_returns_only_requested_carriers(self):
        Carrier.objects.create(**make_validated(carrier_id="MC-A"), score=80.0, score_breakdown={}, record_hash="a" * 64)
        Carrier.objects.create(**make_validated(carrier_id="MC-B"), score=70.0, score_breakdown={}, record_hash="b" * 64)
        result = self.repo.get_existing_carriers(["MC-A"])
        assert "MC-A" in result
        assert "MC-B" not in result

    def test_returns_multiple_carriers(self):
        for i in range(3):
            Carrier.objects.create(
                **make_validated(carrier_id=f"MC-{i}", dot_number=f"100000{i}"),
                score=80.0, score_breakdown={}, record_hash=f"{'a' * 63}{i}",
            )
        result = self.repo.get_existing_carriers(["MC-0", "MC-1", "MC-2"])
        assert len(result) == 3

    def test_empty_list_returns_empty_dict(self):
        result = self.repo.get_existing_carriers([])
        assert result == {}

    def test_single_query_not_n_plus_1(self):
        """Confirma que usa filter() com __in (1 query) e não um loop."""
        for i in range(5):
            Carrier.objects.create(
                **make_validated(carrier_id=f"MC-Q{i}", dot_number=f"200000{i}"),
                score=80.0, score_breakdown={}, record_hash=f"{'b' * 63}{i}",
            )
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            self.repo.get_existing_carriers([f"MC-Q{i}" for i in range(5)])
        assert len(ctx.captured_queries) == 1


@pytest.mark.django_db
class TestUpsert:
    def setup_method(self):
        self.repo = DjangoCarrierRepository()
        self.validated = make_validated()
        self.breakdown = make_breakdown()
        self.record_hash = "c" * 64

    def test_creates_new_carrier_returns_true(self):
        created = self.repo.upsert(self.validated, self.breakdown, self.record_hash)
        assert created is True

    def test_new_carrier_is_persisted(self):
        self.repo.upsert(self.validated, self.breakdown, self.record_hash)
        assert Carrier.objects.filter(carrier_id="MC-TEST-001").exists()

    def test_score_is_saved_correctly(self):
        self.repo.upsert(self.validated, self.breakdown, self.record_hash)
        carrier = Carrier.objects.get(carrier_id="MC-TEST-001")
        assert carrier.score == self.breakdown.total

    def test_record_hash_is_saved(self):
        self.repo.upsert(self.validated, self.breakdown, self.record_hash)
        carrier = Carrier.objects.get(carrier_id="MC-TEST-001")
        assert carrier.record_hash == self.record_hash

    def test_score_breakdown_is_saved(self):
        self.repo.upsert(self.validated, self.breakdown, self.record_hash)
        carrier = Carrier.objects.get(carrier_id="MC-TEST-001")
        assert carrier.score_breakdown == self.breakdown.to_dict()

    def test_update_existing_carrier_returns_false(self):
        self.repo.upsert(self.validated, self.breakdown, self.record_hash)
        new_breakdown = make_breakdown(safety_rating_score=0.0)
        created = self.repo.upsert(self.validated, new_breakdown, "d" * 64)
        assert created is False

    def test_update_changes_score(self):
        self.repo.upsert(self.validated, self.breakdown, self.record_hash)
        new_breakdown = make_breakdown(safety_rating_score=0.0)
        self.repo.upsert(self.validated, new_breakdown, "d" * 64)
        carrier = Carrier.objects.get(carrier_id="MC-TEST-001")
        assert carrier.score == new_breakdown.total

    def test_update_changes_record_hash(self):
        self.repo.upsert(self.validated, self.breakdown, self.record_hash)
        new_hash = "d" * 64
        self.repo.upsert(self.validated, self.breakdown, new_hash)
        carrier = Carrier.objects.get(carrier_id="MC-TEST-001")
        assert carrier.record_hash == new_hash

    def test_fleet_size_defaults_to_1_when_missing(self):
        validated = make_validated()
        del validated["fleet_size"]
        self.repo.upsert(validated, self.breakdown, self.record_hash)
        carrier = Carrier.objects.get(carrier_id="MC-TEST-001")
        assert carrier.fleet_size == 1

    def test_only_one_record_exists_after_multiple_upserts(self):
        self.repo.upsert(self.validated, self.breakdown, self.record_hash)
        self.repo.upsert(self.validated, self.breakdown, self.record_hash)
        self.repo.upsert(self.validated, self.breakdown, self.record_hash)
        assert Carrier.objects.filter(carrier_id="MC-TEST-001").count() == 1

@pytest.mark.django_db
class TestAppendScoreHistory:
    def setup_method(self):
        self.repo = DjangoCarrierRepository()
        self.carrier = Carrier.objects.create(
            **make_validated(), score=85.0, score_breakdown={}, record_hash="e" * 64
        )
        self.breakdown = make_breakdown()

    def test_creates_score_history_entry(self):
        self.repo.append_score_history("MC-TEST-001", self.breakdown)
        assert ScoreHistory.objects.filter(carrier=self.carrier).count() == 1

    def test_score_is_saved_in_history(self):
        self.repo.append_score_history("MC-TEST-001", self.breakdown)
        entry = ScoreHistory.objects.get(carrier=self.carrier)
        assert entry.score == self.breakdown.total

    def test_score_breakdown_is_saved_in_history(self):
        self.repo.append_score_history("MC-TEST-001", self.breakdown)
        entry = ScoreHistory.objects.get(carrier=self.carrier)
        assert entry.score_breakdown == self.breakdown.to_dict()

    def test_multiple_history_entries_accumulate(self):
        b1 = make_breakdown(safety_rating_score=25.0)
        b2 = make_breakdown(safety_rating_score=0.0)
        self.repo.append_score_history("MC-TEST-001", b1)
        self.repo.append_score_history("MC-TEST-001", b2)
        assert ScoreHistory.objects.filter(carrier=self.carrier).count() == 2

    def test_raises_if_carrier_not_found(self):
        with pytest.raises(Carrier.DoesNotExist):
            self.repo.append_score_history("MC-NONEXISTENT", self.breakdown)

    def test_history_is_linked_to_correct_carrier(self):
        other = Carrier.objects.create(
            **make_validated(carrier_id="MC-OTHER", dot_number="9999999"),
            score=50.0, score_breakdown={}, record_hash="f" * 64,
        )
        self.repo.append_score_history("MC-TEST-001", self.breakdown)
        assert ScoreHistory.objects.filter(carrier=other).count() == 0
        assert ScoreHistory.objects.filter(carrier=self.carrier).count() == 1


@pytest.mark.django_db
class TestSaveUploadAudit:
    def setup_method(self):
        self.repo = DjangoCarrierRepository()

    def test_creates_ccf_upload_record(self):
        self.repo.save_upload_audit(5, 3, 1, 1, 0, [])
        assert CCFUpload.objects.count() == 1

    def test_saves_correct_counts(self):
        self.repo.save_upload_audit(
            total=10, new=4, updated=3, unchanged=2, errors=1,
            error_details=[{"carrier_id": "MC-BAD", "error": "invalid"}],
        )
        audit = CCFUpload.objects.first()
        assert audit.total_records == 10
        assert audit.new_count == 4
        assert audit.updated_count == 3
        assert audit.unchanged_count == 2
        assert audit.error_count == 1

    def test_saves_error_details(self):
        details = [{"carrier_id": "MC-ERR", "error": "Validation failed"}]
        self.repo.save_upload_audit(1, 0, 0, 0, 1, details)
        audit = CCFUpload.objects.first()
        assert audit.error_details == details

    def test_saves_empty_error_details(self):
        self.repo.save_upload_audit(5, 5, 0, 0, 0, [])
        audit = CCFUpload.objects.first()
        assert audit.error_details == []

    def test_multiple_audits_accumulate(self):
        self.repo.save_upload_audit(5, 5, 0, 0, 0, [])
        self.repo.save_upload_audit(5, 0, 0, 5, 0, [])
        assert CCFUpload.objects.count() == 2
