"""Step 7R 회귀 — Explicit Validation(F-STEP7-1) + Candidate Scope Authority(F-STEP7-2)."""

from __future__ import annotations

import json

from ghg_agent.agents.orchestrator import build_pipeline
from ghg_agent.domain.mapping import MapperConfig, map_fields
from ghg_agent.domain.models import MappingMethod, SourceProfile
from ghg_agent.domain.normalization import normalize_payload
from ghg_agent.domain.validation import ValidationConfig, validate_mapping_result
from ghg_agent.governance import build_context
from ghg_agent.governance.candidate_scope import load_candidate_inventory
from ghg_agent.llm.client import MockLLMClient
from tests.conftest import load_fixture, requires_registry, requires_skill


def _map(reference, skill, payload, scope=None, profile=SourceProfile.NOON_REPORT):
    fields = normalize_payload(payload, profile)
    res = map_fields(fields, profile, reference, skill, MockLLMClient(),
                     MapperConfig(candidate_scope=scope), "s7r")
    val = validate_mapping_result(res, fields, reference, skill, ValidationConfig())
    return res, val, fields


def _field(res, name):
    return next(f for f in res.fields if f.source_name == name)


# --- B. Explicit validation (F-STEP7-1) ---

@requires_registry
@requires_skill
class TestExplicitValidation:
    def test_explicit_valid_value_promoted_after_validation(self, reference, skill):
        res, _, _ = _map(reference, skill, {"report_datetime": "2026-08-02T12:00:00+00:00", "IMO0616": 12.5})
        f = _field(res, "IMO0616")
        assert f.mapping_method == MappingMethod.EXPLICIT_IDENTIFIER_VALIDATED
        assert f.imo_data_number == "IMO0616" and f.confidence == 1.0 and f.validator_status == "PASS"

    def test_explicit_invalid_type_has_no_final_mapping(self, reference, skill):
        res, _, _ = _map(reference, skill, {"IMO0616": "not-a-number"})
        f = _field(res, "IMO0616")
        assert f.imo_data_number is None and f.confidence is None
        assert f.mapping_method == MappingMethod.UNMAPPED

    def test_explicit_invalid_code_has_no_final_mapping(self, reference, skill):
        # IMO0597 Event type coded + 잘못된 코드값 → code-list 검증 실패 (F-STEP7-1)
        res, _, _ = _map(reference, skill, {"IMO0597": "NOT_A_CODE"}, profile=SourceProfile.EVENT_REPORT)
        f = _field(res, "IMO0597")
        assert f.imo_data_number is None and f.confidence is None
        assert f.mapping_method == MappingMethod.UNMAPPED
        assert any("CODE_VALUE_INVALID" in w for w in f.warnings)

    def test_explicit_not_pass_before_validation_visible_in_result(self, reference, skill):
        # M-06: mapping result 만 조회해도 실패값이 PASS/1.0 로 보이지 않음
        res, _, _ = _map(reference, skill, {"IMO0597": "NOT_A_CODE"}, profile=SourceProfile.EVENT_REPORT)
        f = _field(res, "IMO0597")
        assert f.validator_status != "PASS" and f.confidence != 1.0

    def test_fabricated_explicit_id_rejected(self, reference, skill):
        nonexist = f"IMO{max(int(n[3:]) for n in reference._elements) + 1:04d}"
        res, _, _ = _map(reference, skill, {"ref": nonexist})
        f = _field(res, "ref")
        assert f.imo_data_number is None
        assert any("IMO_ID_NOT_FOUND" in w for w in f.warnings)


# --- C. Candidate scope (F-STEP7-2) ---

@requires_registry
@requires_skill
class TestCandidateScope:
    def test_inventory_loads_and_hash_matches(self, settings):
        inv = load_candidate_inventory(settings.candidate_inventory_path)
        assert inv.bound and inv.load_status == "BOUND"
        assert inv.element_count >= 1 and inv.approved is False

    def test_candidate_subset_binding_success(self, settings):
        inv = load_candidate_inventory(settings.candidate_inventory_path)
        ctx = build_context(settings, reference_ready=True, candidate_set_ready=True,
                            candidate_inventory=inv)
        assert ctx.candidate_scope_enforcement is True
        assert ctx.candidate_mapping_eligible is True

    def test_candidate_subset_hash_mismatch_fail_closed(self, settings, tmp_path):
        bad = tmp_path / "inv.json"
        bad.write_text(json.dumps({"candidate_set_id": "x", "version": "1",
                                   "imo_data_numbers": ["IMO0616"], "sha256": "deadbeef"}), encoding="utf-8")
        inv = load_candidate_inventory(bad)
        assert inv.load_status == "INVALID" and not inv.bound
        ctx = build_context(settings, reference_ready=True, candidate_set_ready=True, candidate_inventory=inv)
        assert ctx.candidate_mapping_eligible is False  # fail-closed, full registry fallback 없음

    def test_candidate_subset_missing_fail_closed(self, settings, tmp_path):
        inv = load_candidate_inventory(tmp_path / "nope.json")
        assert inv.load_status == "UNBOUND" and not inv.bound
        ctx = build_context(settings, reference_ready=True, candidate_set_ready=True, candidate_inventory=inv)
        assert ctx.candidate_mapping_eligible is False

    def test_full_registry_element_outside_subset_rejected(self, reference, skill, settings):
        inv = load_candidate_inventory(settings.candidate_inventory_path)
        # full registry 에는 있으나 subset 밖인 실제 element (set difference)
        outside = next(n for n in sorted(reference._elements) if n not in inv.ids)
        assert reference.exists(outside) and outside not in inv.ids
        res, _, _ = _map(reference, skill, {"ref": outside}, scope=inv.ids)
        f = _field(res, "ref")
        assert f.imo_data_number is None
        assert f.validator_status == "OUT_OF_SCOPE"
        assert any("IMO_ELEMENT_OUTSIDE_APPROVED_CANDIDATE_SCOPE" in w for w in f.warnings)
        assert res.metrics["candidate_scope_rejected"] == 1

    def test_subset_element_accepted(self, reference, skill, settings):
        inv = load_candidate_inventory(settings.candidate_inventory_path)
        # IMO0616(Speed through water)는 subset 안 → 정상 매핑
        res, _, _ = _map(reference, skill,
                         {"report_datetime": "2026-08-02T12:00:00+00:00",
                          "speed_through_water": {"value": 12.0, "unit": "knot"}}, scope=inv.ids)
        f = _field(res, "speed_through_water")
        assert f.imo_data_number == "IMO0616" and f.mapping_method == MappingMethod.NORMALIZED_EXACT_REFERENCE

    def test_candidate_does_not_imply_requiredness(self, settings):
        inv = load_candidate_inventory(settings.candidate_inventory_path)
        ctx = build_context(settings, reference_ready=True, candidate_set_ready=True, candidate_inventory=inv)
        assert ctx.candidate_mapping_eligible is True
        assert ctx.requiredness_profile_approved is False
        assert ctx.executable_mapping_eligible is False


# --- D. governance flags unchanged + API/pipeline consistency ---

@requires_registry
@requires_skill
class TestGovernanceAndConsistency:
    def test_governance_flags_unchanged(self, settings):
        pipe = build_pipeline(settings)
        base = {"candidate_mapping_eligible": True, "requiredness_profile_approved": False,
                "executable_mapping_eligible": False, "actual_normalization_eligible": False,
                "kr_gears_actual_delivery_allowed": False}
        assert pipe.governance.flags() == base
        assert pipe.governance.candidate_scope_enforcement is True

    def test_api_and_pipeline_explicit_result_consistent(self, settings):
        from fastapi.testclient import TestClient

        from ghg_agent.api.app import create_app
        client = TestClient(create_app(settings))
        payload = {"report_datetime": "2026-08-02T12:00:00+00:00", "IMO0616": 12.5}
        api = client.post("/api/v1/map", json={"profile": "NOON_REPORT", "payload": payload,
                                               "correlation_id": "s7r-api"}).json()
        api_field = next(f for f in api["mapping_result"]["fields"] if f["source_name"] == "IMO0616")
        pipe = build_pipeline(settings)
        res, _, _ = _map(pipe.reference, pipe.skill, payload, scope=pipe.candidate_scope)
        pf = _field(res, "IMO0616")
        assert api_field["imo_data_number"] == pf.imo_data_number
        assert api_field["mapping_method"] == pf.mapping_method.value

    def test_noon_regression(self, settings):
        from ghg_agent.evidence import verify_evidence
        st = build_pipeline(settings).run(load_fixture("noon_report_valid.json"), "application/json")
        assert st.status.value == "REVIEW_REQUIRED"
        assert verify_evidence(settings.audit_log_dir / st.correlation_id)["ok"]

    def test_event_regression(self, settings):
        from ghg_agent.evidence import verify_evidence
        st = build_pipeline(settings).run(load_fixture("event_departure.json"), "application/json")
        assert st.status.value == "REVIEW_REQUIRED"
        assert verify_evidence(settings.audit_log_dir / st.correlation_id)["ok"]


# --- F-STEP7-3: batch NOT_VERIFIED 중복 제거 ---

@requires_registry
@requires_skill
def test_batch_chunk_failure_no_duplicate_not_verified(reference, skill, monkeypatch):
    payload = {f"f{i}": "IMO0616" for i in range(600)}
    fields = normalize_payload(payload, SourceProfile.NOON_REPORT)
    res = map_fields(fields, SourceProfile.NOON_REPORT, reference, skill, MockLLMClient(),
                     MapperConfig(), "s7r-batch")
    import ghg_agent.domain.validation as valmod
    calls = {"n": 0}
    orig = skill.invoke

    def flaky(tool, args, correlation_id=None):
        if tool == "validate_mapping":
            calls["n"] += 1
            if calls["n"] == 2:
                from ghg_agent.adapters.skill_adapter import SkillAdapterError
                raise SkillAdapterError("SKILL_EXECUTION_ERROR", "injected")
        return orig(tool, args, correlation_id)

    monkeypatch.setattr(skill, "invoke", flaky)
    val = validate_mapping_result(res, fields, reference, skill, ValidationConfig())
    # 실패 청크(100 필드) → NOT_VERIFIED item 100 (2중 아님)
    nv_items = [i for i in val.items if i.verdict == valmod.ValidationVerdict.NOT_VERIFIED
                and i.check == "skill_registry_validation"]
    paths = [i.source_path for i in nv_items]
    assert len(paths) == len(set(paths))  # 중복 없음
    assert val.overall.value != "PASS"
