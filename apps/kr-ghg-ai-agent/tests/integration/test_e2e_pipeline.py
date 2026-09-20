"""TS-3/E2E-1~5: Mock LLM + Real Skill + Mock delivery 전체 파이프라인.

integration matrix (본 파일): LLM=mock, Skill=real, MCP=off, delivery=mock.
KR GEARs 제출 계약이 PROVISIONAL 이므로 정상 실행의 최종 상태는
DELIVERED 가 아니라 REVIEW_REQUIRED 다 (성공 위장 금지, O-3).
"""

from __future__ import annotations

import json

import pytest

from ghg_agent.agents.orchestrator import DuplicateRunError, build_pipeline
from ghg_agent.domain.models import RunStatus
from ghg_agent.evidence import verify_evidence
from tests.conftest import load_fixture, requires_registry, requires_skill


@pytest.fixture()
def pipeline(settings):
    return build_pipeline(settings)


def run_fixture(pipeline, name: str):
    return pipeline.run(load_fixture(name), "application/json")


def evidence_json(settings, correlation_id: str, filename: str):
    path = settings.audit_log_dir / correlation_id / filename
    return json.loads(path.read_text(encoding="utf-8"))


@requires_registry
@requires_skill
class TestE2EScenarios:
    def test_e2e1_vessel_performance(self, pipeline, settings):
        state = run_fixture(pipeline, "vessel_performance_valid.json")
        # 매핑은 전부 결정론 확정, 미검증 IMO 없음
        mapping = evidence_json(settings, state.correlation_id, "mapping-result.json")
        assert mapping["metrics"]["unmapped"] == 0
        assert mapping["metrics"]["llm_invocations"] == 0
        for field in mapping["fields"]:
            assert field["imo_data_number"] is not None
            assert field["mapping_method"] != "UNMAPPED"
            assert field["reference_model_version"] == "FAL50"
        # PROVISIONAL contract → 최종 REVIEW_REQUIRED (mock delivery 는 수행됨)
        assert state.status == RunStatus.REVIEW_REQUIRED
        assert state.error == "KR_GEARS_CONTRACT_PROVISIONAL"
        delivery = evidence_json(settings, state.correlation_id, "delivery-result.json")
        assert delivery["mode"] == "mock" and delivery["real_call"] is False
        # Evidence 무결성
        check = verify_evidence(settings.audit_log_dir / state.correlation_id)
        assert check["ok"] is True

    def test_e2e2_noon_report(self, pipeline, settings):
        state = run_fixture(pipeline, "noon_report_valid.json")
        assert state.status == RunStatus.REVIEW_REQUIRED  # PROVISIONAL 계약 때문
        output = evidence_json(settings, state.correlation_id, "kr-gears-output.json")
        assert output["contract_status"] == "PROVISIONAL"
        assert output["payload"]["voyage"] == "SYN-VOY-002"
        # provenance 완전성
        mapping = evidence_json(settings, state.correlation_id, "mapping-result.json")
        mapped_paths = {
            f["source_path"] for f in mapping["fields"] if f["imo_data_number"]
        }
        prov_paths = {p["source_path"] for p in output["provenance"]}
        assert mapped_paths == prov_paths
        # 실계약 verdict envelope 존재 (validator KrGearsReport 로 검증됨)
        assert output["verdict_report"]["compendium_version"] == "FAL50"
        delivery = evidence_json(settings, state.correlation_id, "delivery-result.json")
        assert delivery["mode"] == "mock"
        manifest = evidence_json(settings, state.correlation_id, "manifest.json")
        assert manifest["synthetic_data"] is True
        assert manifest["skill_real_or_mock"] == "real"
        assert manifest["llm_provider"] == "mock"
        assert manifest["kr_gears_contract_status"] == "PROVISIONAL"

    def test_e2e3_event_reports_grouping(self, pipeline, settings):
        from ghg_agent.adapters.kr_gears import group_events_by_voyage
        from ghg_agent.domain.models import TransformResult

        names = [
            "event_departure.json",
            "event_bunkering.json",
            "event_anchoring.json",
            "event_arrival.json",
        ]
        states = [run_fixture(pipeline, name) for name in names]
        by_id = {s.correlation_id: s for s in states}
        assert len(by_id) == 4  # 이벤트 구분 유지

        # BUNKERING: code list 미확인 이벤트 — 발명 없이 REVIEW_REQUIRED
        bunkering = by_id["SYN-EV-BNK-0001"]
        assert bunkering.status == RunStatus.REVIEW_REQUIRED
        assert bunkering.transform_result is None
        validation = evidence_json(settings, "SYN-EV-BNK-0001", "validation-result.json")
        assert any(i["code"] == "CODE_VALUE_INVALID" for i in validation["items"])

        # 나머지 3개는 변환까지 도달 (최종 REVIEW_REQUIRED — PROVISIONAL 계약)
        transformed = [
            s for s in states
            if s.transform_result is not None
        ]
        assert {s.correlation_id for s in transformed} == {
            "SYN-EV-DEP-0001", "SYN-EV-ANC-0001", "SYN-EV-ARR-0001",
        }
        grouped = group_events_by_voyage(
            [TransformResult.model_validate(s.transform_result.model_dump()) for s in transformed]
        )
        voyage = grouped["voyages"]["SYN-VOY-002"]
        # timestamp 결정론 정렬: 출항(08-01) → 투묘(08-03) → 입항(08-04)
        assert [e["correlation_id"] for e in voyage] == [
            "SYN-EV-DEP-0001", "SYN-EV-ANC-0001", "SYN-EV-ARR-0001",
        ]
        for event in voyage:
            assert event["provenance_refs"]  # 항차 수준 provenance

    def test_e2e4_ambiguous_mapping(self, pipeline, settings):
        state = run_fixture(pipeline, "noon_report_ambiguous.json")
        assert state.status == RunStatus.REVIEW_REQUIRED
        mapping = evidence_json(settings, state.correlation_id, "mapping-result.json")
        distance = next(
            f for f in mapping["fields"] if f["source_name"] == "distance"
        )
        # 확정 매핑 없음, 후보 보존, 사유 기록
        assert distance["imo_data_number"] is None
        assert distance["mapping_method"] == "UNMAPPED"
        assert distance["candidate_list"]
        assert state.transform_result is None

    def test_e2e5_fabricated_imo_defense(self, pipeline, settings, reference):

        assert not reference.exists("IMO9999")  # fixture 전제 확인
        state = run_fixture(pipeline, "vessel_performance_negative.json")
        assert state.status == RunStatus.REVIEW_REQUIRED
        mapping = evidence_json(settings, state.correlation_id, "mapping-result.json")
        hint = next(f for f in mapping["fields"] if f["source_name"] == "reference_hint")
        assert hint["imo_data_number"] is None
        assert any("IMO_ID_NOT_FOUND" in w for w in hint["warnings"])
        assert mapping["metrics"]["fabricated_candidate_rejections"] >= 1
        # 변환 미수행
        assert not (settings.audit_log_dir / state.correlation_id / "kr-gears-output.json").exists()

    def test_duplicate_correlation_id_conflict(self, pipeline, settings):
        run_fixture(pipeline, "noon_report_valid.json")
        with pytest.raises(DuplicateRunError):
            run_fixture(pipeline, "noon_report_valid.json")

    def test_evidence_no_overwrite(self, settings):
        from ghg_agent.evidence import EvidenceError, EvidenceWriter

        writer = EvidenceWriter(settings.audit_log_dir, "overwrite-check")
        writer.write_json("profile-result.json", {"a": 1})
        with pytest.raises(EvidenceError):
            writer.write_json("profile-result.json", {"a": 2})
