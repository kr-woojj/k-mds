"""TS-1/TS-5: 결정론 검증 규칙과 KR GEARs 변환/provenance."""

from __future__ import annotations

import pytest

from ghg_agent.adapters.kr_gears import deliver, transform
from ghg_agent.domain.mapping import MapperConfig, map_fields
from ghg_agent.domain.models import (
    ContractStatus,
    SourceProfile,
    ValidationVerdict,
)
from ghg_agent.domain.normalization import normalize_payload
from ghg_agent.domain.validation import ValidationConfig, validate_mapping_result
from ghg_agent.llm.client import MockLLMClient
from tests.conftest import load_fixture_json, requires_registry, requires_skill


@pytest.fixture()
def noon_run(reference, skill):
    payload = load_fixture_json("noon_report_valid.json")
    fields = normalize_payload(payload, SourceProfile.NOON_REPORT)
    mapping = map_fields(
        fields, SourceProfile.NOON_REPORT, reference, skill,
        MockLLMClient(), MapperConfig(), "unit-noon-001",
    )
    validation = validate_mapping_result(
        mapping, fields, reference, skill, ValidationConfig()
    )
    return payload, fields, mapping, validation


@requires_registry
@requires_skill
class TestValidation:
    def test_noon_valid_passes(self, noon_run):
        _, _, mapping, validation = noon_run
        assert mapping.metrics["unmapped"] == 0
        assert validation.overall in (ValidationVerdict.PASS, ValidationVerdict.WARNING)
        assert validation.fail_count == 0

    def test_code_list_value_checked(self, noon_run, reference, skill):
        payload = load_fixture_json("noon_report_valid.json")
        payload["fuel_type_code"] = "NOT_A_FUEL"
        fields = normalize_payload(payload, SourceProfile.NOON_REPORT)
        mapping = map_fields(
            fields, SourceProfile.NOON_REPORT, reference, skill,
            MockLLMClient(), MapperConfig(), "unit-noon-002",
        )
        validation = validate_mapping_result(
            mapping, fields, reference, skill, ValidationConfig()
        )
        codes = {i.code for i in validation.items}
        assert "CODE_VALUE_INVALID" in codes
        assert validation.overall == ValidationVerdict.FAIL

    def test_official_format_inconsistency_fails_closed(self, reference, skill):
        """FAL50 원본에서 IMO0654(Fuel type, coded) format 은 n..10 인데 공식
        code list 값은 'HFO' 등 문자열 — 이 공식 데이터 불일치는 은폐하지 않고
        DATATYPE_HARD_CONFLICT 로 fail-closed 됨을 고정한다 (known limitation)."""
        payload = load_fixture_json("noon_report_valid.json")
        payload["fuel_type_code"] = "HFO"
        fields = normalize_payload(payload, SourceProfile.NOON_REPORT)
        mapping = map_fields(
            fields, SourceProfile.NOON_REPORT, reference, skill,
            MockLLMClient(), MapperConfig(), "unit-noon-fmt",
        )
        validation = validate_mapping_result(
            mapping, fields, reference, skill, ValidationConfig()
        )
        assert any(
            i.code == "DATATYPE_HARD_CONFLICT" and i.imo_data_number == "IMO0654"
            for i in validation.items
        )
        assert validation.overall == ValidationVerdict.FAIL

    def test_required_field_missing(self, reference, skill):
        payload = load_fixture_json("noon_report_mandatory_missing.json")
        fields = normalize_payload(payload, SourceProfile.NOON_REPORT)
        mapping = map_fields(
            fields, SourceProfile.NOON_REPORT, reference, skill,
            MockLLMClient(), MapperConfig(), "unit-noon-003",
        )
        validation = validate_mapping_result(
            mapping, fields, reference, skill, ValidationConfig()
        )
        assert any(i.code == "REQUIRED_FIELD_MISSING" for i in validation.items)
        assert validation.overall == ValidationVerdict.FAIL

    def test_skill_unavailable_is_not_verified(self, noon_run, reference, settings):
        from ghg_agent.adapters.skill_adapter import ImoMappingSkillAdapter

        _, fields, mapping, _ = noon_run
        broken = ImoMappingSkillAdapter(
            skill_path=settings.imo_mapping_skill_path,
            registry_db_path=settings.registry_db_path.with_name("missing.sqlite3"),
        )
        validation = validate_mapping_result(
            mapping, fields, reference, broken, ValidationConfig()
        )
        # fail-closed: Skill 없이 성공 선언 금지
        assert validation.overall in (ValidationVerdict.NOT_VERIFIED, ValidationVerdict.FAIL)
        assert validation.not_verified_count > 0


@requires_registry
@requires_skill
class TestTransform:
    def test_noon_transform_provenance(self, noon_run):
        _, fields, mapping, validation = noon_run
        result = transform(mapping, fields, validation, "unit-noon-001")
        assert result.contract_status == ContractStatus.PROVISIONAL
        assert result.payload["contract_status"] == "PROVISIONAL"
        assert result.payload["voyage"] == "SYN-VOY-002"
        # source→target provenance 완전성
        mapped_paths = {m.source_path for m in mapping.fields if m.imo_data_number}
        prov_paths = {p.source_path for p in result.provenance}
        assert mapped_paths == prov_paths
        for p in result.provenance:
            assert p.transformation_rule_id == "TR-NOON-1"
            assert p.contract_status == ContractStatus.PROVISIONAL
            assert p.conversion_applied is False
        # 실계약 verdict envelope 은 validator Pydantic 모델로 검증됨
        assert result.verdict_report is not None
        assert result.verdict_report["compendium_version"] == "FAL50"
        assert result.verdict_report["validation_status"] in ("PASS", "REVIEW_REQUIRED", "FAIL")

    def test_transform_rejects_failed_validation(self, noon_run):
        _, fields, mapping, validation = noon_run
        failed = validation.model_copy(update={"overall": ValidationVerdict.FAIL})
        with pytest.raises(ValueError):
            transform(mapping, fields, failed, "unit-noon-004")

    def test_http_delivery_blocked_for_provisional(self, noon_run):
        _, fields, mapping, validation = noon_run
        result = transform(mapping, fields, validation, "unit-noon-005")
        outcome = deliver(result, mode="http", api_url="http://127.0.0.1:9/none")
        assert outcome.status == "BLOCKED"
        assert outcome.real_call is False

    def test_mock_delivery_identified(self, noon_run):
        _, fields, mapping, validation = noon_run
        result = transform(mapping, fields, validation, "unit-noon-006")
        outcome = deliver(result, mode="mock")
        assert outcome.status == "DELIVERED"
        assert outcome.real_call is False
        assert outcome.mode == "mock"
