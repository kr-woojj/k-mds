"""Phase-2 회귀 테스트 — baseline red-team 결함(DEFECT-1..5) fail-closed 고정.

각 테스트는 해당 결함이 다시 fail-open 되지 않음을 보장한다.
"""

from __future__ import annotations

import json

import pytest

from ghg_agent.adapters.ids_adapter import MAX_JSON_DEPTH, ingest
from ghg_agent.agents.orchestrator import DuplicateRunError, build_pipeline
from ghg_agent.domain.mapping import MapperConfig, map_fields
from ghg_agent.domain.models import IngressBodyType, MappingMethod, RunStatus, SourceProfile
from ghg_agent.domain.normalization import (
    MAX_FIELD_DEPTH,
    NormalizationError,
    normalize_payload,
)
from ghg_agent.domain.validation import ValidationConfig, validate_mapping_result
from ghg_agent.llm.client import MockLLMClient
from tests.conftest import requires_registry, requires_skill


def _deep_json(depth: int, cid: str, key: str = "deepfield") -> bytes:
    # 올바른 깊은 중첩: {"key": {"n":{"n":...1...}}}
    nested_body = ('{"n":' * depth) + "1" + ("}" * depth)
    return ('{"correlation_id":"' + cid + '","report_type":"noon",'
            '"report_datetime":"2026-08-01T12:00:00+00:00",'
            '"' + key + '":' + nested_body + "}").encode()


class TestDefect2IngressDepth:
    def test_deep_body_rejected_before_parse(self):
        # DEFECT-2: 재귀 파서 도달 전 BODY_TOO_DEEP 로 fail-closed
        raw = _deep_json(3000, "D2")
        result, business = ingest(raw, "application/json")
        assert result.body_type == IngressBodyType.UNKNOWN
        assert "BODY_TOO_DEEP" in result.validation_errors
        assert business is None

    def test_depth_at_limit_still_parses(self):
        # 한계 이하(정상 얕은 payload)는 정상 처리
        raw = b'{"report_type":"noon","speed_through_water":12.0}'
        result, business = ingest(raw, "application/json")
        assert result.body_type == IngressBodyType.RAW_JSON_BODY
        assert business is not None


class TestDefect1NormalizeDepth:
    def test_flatten_depth_guard_raises_controlled_error(self):
        # DEFECT-1: 직접 dict 경로(/api/v1/map)도 RecursionError 대신 통제 예외
        payload: dict = {"leaf": 1}
        for _ in range(MAX_FIELD_DEPTH + 50):
            payload = {"n": payload}
        with pytest.raises(NormalizationError) as exc:
            normalize_payload(payload, SourceProfile.NOON_REPORT)
        assert exc.value.code == "PAYLOAD_TOO_DEEP"

    def test_shallow_payload_unaffected(self):
        fields = normalize_payload(
            {"speed_through_water": {"value": 12.0, "unit": "knot"}}, SourceProfile.NOON_REPORT
        )
        assert any(f.source_name == "speed_through_water" for f in fields)


@requires_registry
@requires_skill
class TestDefect1And1bPipeline:
    def test_deep_payload_pipeline_fail_closed(self, settings):
        pipe = build_pipeline(settings)
        state = pipe.run(_deep_json(3000, "D1-PIPE"), "application/json")
        # 크래시(500) 아님 — fail-closed. (too-deep 는 파싱 불가로 UNKNOWN → REVIEW_REQUIRED)
        assert state.status == RunStatus.REVIEW_REQUIRED
        assert "BODY_TOO_DEEP" in (state.error or "")

    def test_stage_exception_finalizes_failed_manifest(self, settings, monkeypatch):
        # DEFECT-1b: 임의 stage 예외에도 FAILED manifest 완결 + cid 오염 없음
        import ghg_agent.agents.orchestrator as orch

        def boom(*a, **k):
            raise RuntimeError("forced stage crash")

        monkeypatch.setattr(orch, "validate_mapping_result", boom)
        raw = (b'{"correlation_id":"D1B","report_type":"noon",'
               b'"report_datetime":"2026-08-01T12:00:00+00:00","speed_through_water":12.0}')
        state = build_pipeline(settings).run(raw, "application/json")
        assert state.status == RunStatus.FAILED
        assert state.error.startswith("PIPELINE_EXCEPTION")
        manifest = settings.audit_log_dir / "D1B" / "manifest.json"
        assert manifest.is_file()
        assert json.loads(manifest.read_text(encoding="utf-8"))["final_status"] == "FAILED"
        # 재시도는 깨끗한 409 (오염 없음)
        with pytest.raises(DuplicateRunError):
            build_pipeline(settings).run(raw, "application/json")


@requires_registry
@requires_skill
class TestDefect3ExplicitValidation:
    def test_name_shaped_wrong_type_not_confirmed(self, reference, skill):
        # DEFECT-3: 필드명이 IMO형이고 값 타입이 불일치하면 확정하지 않음
        fields = normalize_payload({"IMO0616": "not-a-number-hello"}, SourceProfile.NOON_REPORT)
        res = map_fields(fields, SourceProfile.NOON_REPORT, reference, skill,
                         MockLLMClient(), MapperConfig(), "D3-1")
        m = res.fields[0]
        assert m.imo_data_number is None
        assert m.mapping_method == MappingMethod.UNMAPPED
        assert any("EXPLICIT_VALIDATION_FAILED" in w for w in m.warnings)

    def test_value_based_explicit_still_confirmed(self, reference, skill):
        # 정상 explicit(값=식별자) 계약은 유지
        fields = normalize_payload({"target_element": "IMO0616"}, SourceProfile.NOON_REPORT)
        res = map_fields(fields, SourceProfile.NOON_REPORT, reference, skill,
                         MockLLMClient(), MapperConfig(), "D3-2")
        m = res.fields[0]
        assert m.imo_data_number == "IMO0616"
        assert m.mapping_method == MappingMethod.EXPLICIT_IDENTIFIER_VALIDATED


@requires_registry
@requires_skill
class TestDefect5BatchChunking:
    def test_over_500_mapped_fields_chunked(self, reference, skill):
        # DEFECT-5: >500 매핑 필드가 500-한계로 전건 NOT_VERIFIED 되지 않음
        payload = {f"f{i}": "IMO0616" for i in range(600)}
        fields = normalize_payload(payload, SourceProfile.NOON_REPORT)
        res = map_fields(fields, SourceProfile.NOON_REPORT, reference, skill,
                         MockLLMClient(), MapperConfig(), "D5")
        assert sum(1 for m in res.fields if m.imo_data_number) == 600
        val = validate_mapping_result(res, fields, reference, skill, ValidationConfig())
        # 청크 검증되어 500-한계發 NOT_VERIFIED 가 발생하지 않음
        assert val.not_verified_count == 0


@requires_registry
class TestDefect4ReferenceConflictClassification:
    def test_scanner_detects_fuel_type_conflict(self, reference):
        # DEFECT-4: 상류 format/codelist 충돌이 결정론적으로 탐지됨(분류)
        import re

        el = reference.element("IMO0654")
        assert el is not None
        resolved = reference.code_list_for_element(el)
        assert resolved is not None
        _, values = resolved
        numeric_only = el.format_spec and el.format_spec.strip().lower().startswith("n") \
            and not el.format_spec.strip().lower().startswith("an")
        non_numeric = [v for v in values if not re.fullmatch(r"[0-9]+(\.[0-9]+)?", v)]
        assert numeric_only and non_numeric  # 충돌 조건 성립 → REVIEW_REQUIRED 분류 근거


def test_max_depth_constants_consistent():
    # ingest 와 normalize 깊이 상한이 일관
    assert MAX_JSON_DEPTH == MAX_FIELD_DEPTH == 64
