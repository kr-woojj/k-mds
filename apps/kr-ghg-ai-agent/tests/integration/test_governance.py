"""Governance Runtime Binding — GovernanceAuthorityContext 강제 검증.

현재 상태의 5개 플래그가 정확히 강제되고, Authority 바인딩 변화가 플래그와
파이프라인 게이트에 실제로 반영됨을 확인한다(하드코딩 아님).
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from ghg_agent.agents.orchestrator import PipelineState, build_pipeline
from ghg_agent.api.app import create_app
from ghg_agent.domain.models import (
    ContractStatus,
    RunStatus,
    SourceProfile,
    TransformResult,
)
from ghg_agent.governance import (
    AuthorityBinding,
    AuthorityKind,
    AuthorityStatus,
    GovernanceAuthorityContext,
    RuntimeBinding,
    build_context,
)
from tests.conftest import load_fixture, requires_registry, requires_skill

REQUIRED_CURRENT_FLAGS = {
    "candidate_mapping_eligible": True,
    "requiredness_profile_approved": False,
    "executable_mapping_eligible": False,
    "actual_normalization_eligible": False,
    "kr_gears_actual_delivery_allowed": False,
}


def _binding(kind, status):
    return AuthorityBinding(kind=kind, status=status)


def _context(reference, candidate_set, requiredness, authoring, delivery):
    return GovernanceAuthorityContext(
        reference=_binding(AuthorityKind.REFERENCE, reference),
        candidate_set=_binding(AuthorityKind.CANDIDATE_SET, candidate_set),
        requiredness=_binding(AuthorityKind.REQUIREDNESS, requiredness),
        authoring=_binding(AuthorityKind.AUTHORING, authoring),
        delivery=_binding(AuthorityKind.DELIVERY, delivery),
        runtime_binding=RuntimeBinding(
            imo_mapping_skill_path="x", registry_db_path="y", code_lists_path="z",
            kr_gears_delivery_mode="mock",
        ),
    )


class TestFlagDerivation:
    def test_current_state_flags_exact(self, settings):
        # F-STEP7-2: candidate_set BOUND 은 승인 후보 집합(inventory) BOUND 를 요구.
        from ghg_agent.governance.candidate_scope import load_candidate_inventory
        inv = load_candidate_inventory(settings.candidate_inventory_path)
        ctx = build_context(settings, reference_ready=True, candidate_set_ready=True,
                            candidate_inventory=inv)
        assert ctx.flags() == REQUIRED_CURRENT_FLAGS
        assert ctx.candidate_scope_enforcement is True

    def test_all_approved_enables_execution(self):
        B = AuthorityStatus.BOUND
        ctx = _context(B, B, B, B, B)
        assert ctx.executable_mapping_eligible is True
        assert ctx.kr_gears_actual_delivery_allowed is True
        assert ctx.actual_normalization_eligible is True

    def test_reference_unbound_blocks_candidate_mapping(self):
        ctx = _context(AuthorityStatus.UNBOUND, AuthorityStatus.BOUND,
                       AuthorityStatus.PROVISIONAL, AuthorityStatus.PROVISIONAL,
                       AuthorityStatus.UNBOUND)
        assert ctx.candidate_mapping_eligible is False

    def test_delivery_needs_executable(self):
        # delivery 승인만으로는 부족 — executable 이 함께여야 실제 delivery 허용
        ctx = _context(AuthorityStatus.BOUND, AuthorityStatus.BOUND,
                       AuthorityStatus.PROVISIONAL, AuthorityStatus.PROVISIONAL,
                       AuthorityStatus.BOUND)
        assert ctx.kr_gears_actual_delivery_allowed is False


@requires_registry
@requires_skill
class TestPipelineGovernanceGates:
    def test_candidate_mapping_blocked_when_authority_unbound(self, settings):
        pipe = build_pipeline(settings)
        pipe.governance = _context(  # reference 미승인 → candidate_mapping_eligible=false
            AuthorityStatus.UNBOUND, AuthorityStatus.BOUND, AuthorityStatus.PROVISIONAL,
            AuthorityStatus.PROVISIONAL, AuthorityStatus.UNBOUND)
        state = pipe.run(load_fixture("noon_report_valid.json"), "application/json")
        assert state.status == RunStatus.REVIEW_REQUIRED
        assert state.error == "GOVERNANCE_CANDIDATE_MAPPING_BLOCKED"

    def test_delivered_requires_executable_and_delivery(self, settings):
        pipe = build_pipeline(settings)
        state = PipelineState(correlation_id="GOV-DEL")
        state.status = RunStatus.TRANSFORMED
        state.transform_result = TransformResult(
            correlation_id="GOV-DEL", profile=SourceProfile.NOON_REPORT,
            contract_status=ContractStatus.CONTRACT_VERIFIED, payload={},
        )
        # 현재 governance(executable=false) → CONTRACT_VERIFIED 여도 DELIVERED 아님
        out = pipe._node_deliver(state.model_copy(deep=True))
        assert out.status == RunStatus.REVIEW_REQUIRED
        assert out.error == "GOVERNANCE_EXECUTABLE_MAPPING_BLOCKED"

        # 모든 Authority 승인 → 동일 입력이 DELIVERED
        pipe.governance = _context(*([AuthorityStatus.BOUND] * 5))
        out2 = pipe._node_deliver(state.model_copy(deep=True))
        assert out2.status == RunStatus.DELIVERED

    def test_http_delivery_blocked_by_governance(self, settings):
        from dataclasses import replace

        s = replace(settings, kr_gears_delivery_mode="http",
                    kr_gears_api_url="http://127.0.0.1:9/none")
        pipe = build_pipeline(s)
        state = PipelineState(correlation_id="GOV-HTTP")
        state.status = RunStatus.TRANSFORMED
        state.transform_result = TransformResult(
            correlation_id="GOV-HTTP", profile=SourceProfile.NOON_REPORT,
            contract_status=ContractStatus.PROVISIONAL, payload={},
        )
        out = pipe._node_deliver(state.model_copy(deep=True))
        assert out.delivery_result.status == "BLOCKED"
        assert out.delivery_result.detail == "GOVERNANCE_DELIVERY_NOT_ALLOWED"
        assert out.delivery_result.real_call is False


@requires_registry
@requires_skill
class TestGovernanceEvidenceAndApi:
    def test_evidence_records_governance(self, settings):
        pipe = build_pipeline(settings)
        state = pipe.run(load_fixture("noon_report_valid.json"), "application/json")
        d = settings.audit_log_dir / state.correlation_id
        ctx = json.loads((d / "governance-context.json").read_text(encoding="utf-8"))
        assert ctx["enforced_flags"] == REQUIRED_CURRENT_FLAGS
        assert ctx["authorities"]["ReferenceAuthority"]["approved"] is True
        manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["governance_flags"] == REQUIRED_CURRENT_FLAGS

    def test_api_governance_endpoint_and_ready(self, settings):
        client = TestClient(create_app(settings))
        gov = client.get("/api/v1/governance")
        assert gov.status_code == 200
        assert gov.json()["enforced_flags"] == REQUIRED_CURRENT_FLAGS
        ready = client.get("/ready")
        assert ready.json()["components"]["governance"]["enforced_flags"] == REQUIRED_CURRENT_FLAGS
