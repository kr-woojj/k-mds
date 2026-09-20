"""TS-1/TS-5: 결정론 우선 매핑, LLM 호출 차단, fabricated IMO 거부."""

from __future__ import annotations

from ghg_agent.domain.mapping import MapperConfig, map_fields
from ghg_agent.domain.models import MappingMethod, SourceProfile
from ghg_agent.domain.normalization import normalize_payload
from ghg_agent.llm.client import MockLLMClient
from tests.conftest import (
    load_fixture_json,
    nonexistent_imo_number,
    requires_registry,
    requires_skill,
)


class ForbiddenLLM(MockLLMClient):
    """호출되면 즉시 실패 — 결정론 경로 검증용."""

    def generate_candidates(self, **kwargs):
        raise AssertionError("결정론으로 해결 가능한 필드에 LLM 이 호출되었다")


@requires_registry
@requires_skill
class TestDeterministicFirst:
    def test_exact_fields_never_call_llm(self, reference, skill):
        payload = load_fixture_json("vessel_performance_valid.json")
        fields = normalize_payload(payload, SourceProfile.VESSEL_PERFORMANCE)
        result = map_fields(
            fields, SourceProfile.VESSEL_PERFORMANCE, reference, skill,
            ForbiddenLLM(), MapperConfig(), "test-det-001",
        )
        assert result.metrics["llm_invocations"] == 0
        methods = {m.source_name: m.mapping_method for m in result.fields}
        assert methods["speed_through_water"] == MappingMethod.NORMALIZED_EXACT_REFERENCE
        assert methods["voyage_no"] == MappingMethod.ALIAS_REFERENCE
        mapped = {m.source_name: m.imo_data_number for m in result.fields}
        assert mapped["speed_through_water"] == "IMO0616"
        assert mapped["total_fuel_quantity_consumed"] == "IMO0669"
        assert mapped["fuel_quantity_remaining_onboard"] == "IMO0674"
        assert result.metrics["unmapped"] == 0
        for m in result.fields:
            assert m.reference_model_version == "FAL50"

    def test_explicit_identifier_validated(self, reference, skill):
        fields = normalize_payload(
            {"target_element": "IMO0616"}, SourceProfile.VESSEL_PERFORMANCE
        )
        result = map_fields(
            fields, SourceProfile.VESSEL_PERFORMANCE, reference, skill,
            ForbiddenLLM(), MapperConfig(), "test-det-002",
        )
        m = result.fields[0]
        assert m.mapping_method == MappingMethod.EXPLICIT_IDENTIFIER_VALIDATED
        assert m.imo_data_number == "IMO0616"
        assert m.confidence == 1.0

    def test_fabricated_imo_identifier_rejected(self, reference, skill):
        fake = nonexistent_imo_number(reference)
        fields = normalize_payload({"reference_hint": fake}, SourceProfile.VESSEL_PERFORMANCE)
        result = map_fields(
            fields, SourceProfile.VESSEL_PERFORMANCE, reference, skill,
            ForbiddenLLM(), MapperConfig(), "test-det-003",
        )
        m = result.fields[0]
        assert m.imo_data_number is None
        assert m.mapping_method == MappingMethod.UNMAPPED
        assert m.validator_status == "FAIL"
        assert any("IMO_ID_NOT_FOUND" in w for w in m.warnings)
        assert result.metrics["fabricated_candidate_rejections"] == 1
        # 형식 유효 ≠ 의미 유효 — candidate_list 에는 FAIL 로 남는다
        assert m.candidate_list[0].validator_status == "FAIL"

    def test_ambiguous_field_not_auto_confirmed(self, reference, skill):
        payload = load_fixture_json("noon_report_ambiguous.json")
        fields = [
            f for f in normalize_payload(payload, SourceProfile.NOON_REPORT)
            if f.source_name == "distance"
        ]
        llm = MockLLMClient()
        result = map_fields(
            fields, SourceProfile.NOON_REPORT, reference, skill,
            llm, MapperConfig(), "test-amb-001",
        )
        m = result.fields[0]
        # E2E-4: 확정 금지, 후보는 candidate_list 에 보존, 사유 기록
        assert m.mapping_method in (MappingMethod.UNMAPPED, MappingMethod.LLM_SUGGESTED_AND_VALIDATED)
        if m.mapping_method == MappingMethod.UNMAPPED:
            assert m.imo_data_number is None
            assert m.candidate_list, "후보 목록이 보존되어야 한다"

    def test_llm_fabricated_candidate_rejected(self, reference, skill):
        from ghg_agent.llm.client import LLMCandidate, LLMCandidateBatch

        fake = nonexistent_imo_number(reference)
        llm = MockLLMClient(
            forced_batch=LLMCandidateBatch(
                candidates=[
                    LLMCandidate(imo_data_number=fake, reason="fabricated", confidence=0.99)
                ]
            )
        )
        fields = normalize_payload(
            {"mystery_quantity": {"value": 1.0, "unit": "tonne", "description": "unknown fuel figure"}},
            SourceProfile.NOON_REPORT,
        )
        result = map_fields(
            fields, SourceProfile.NOON_REPORT, reference, skill, llm,
            MapperConfig(), "test-fab-001",
        )
        m = result.fields[0]
        assert m.imo_data_number is None
        fabricated = [c for c in m.candidate_list if c.imo_data_number == fake]
        assert fabricated and fabricated[0].validator_status == "FAIL"
        assert result.metrics["fabricated_candidate_rejections"] >= 1


@requires_registry
@requires_skill
def test_skill_failure_blocks_llm_only_path(reference, settings):
    """C-5: Skill 장애 시 LLM 단독 진행 금지."""
    from ghg_agent.adapters.skill_adapter import ImoMappingSkillAdapter

    broken = ImoMappingSkillAdapter(
        skill_path=settings.imo_mapping_skill_path,
        registry_db_path=settings.registry_db_path.with_name("missing.sqlite3"),
    )
    fields = normalize_payload({"mystery_quantity": 1.0}, SourceProfile.NOON_REPORT)

    class TrackingLLM(MockLLMClient):
        called = False

        def generate_candidates(self, **kwargs):
            TrackingLLM.called = True
            return super().generate_candidates(**kwargs)

    result = map_fields(
        fields, SourceProfile.NOON_REPORT, reference, broken,
        TrackingLLM(), MapperConfig(), "test-failclosed-001",
    )
    m = result.fields[0]
    assert m.imo_data_number is None
    assert any("REGISTRY_DB_NOT_FOUND" in w or "skill 실패" in w for w in m.warnings)
    assert TrackingLLM.called is False
