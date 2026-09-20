"""OrchestratorAgent (A-1) — LangGraph StateGraph 기반 결정론 파이프라인.

패턴 근거: kr-ai-agents/lab/09_langgraph_workflows.ipynb 의 실행 코드
(StateGraph + typed state + add_conditional_edges). Agent 간 상태는
Pydantic 모델(PipelineState)로만 전달된다 (D-2).

상태 전이는 ALLOWED_TRANSITIONS 로 강제되며 잘못된 전이는 즉시 실패한다.
동일 correlation_id 는 Evidence 존재 여부로 idempotency conflict 처리한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field

from ghg_agent.adapters.ids_adapter import ResourceLimits, ingest
from ghg_agent.adapters.kr_gears import deliver, transform
from ghg_agent.adapters.skill_adapter import ImoMappingSkillAdapter
from ghg_agent.config import PROJECT_ROOT, Settings
from ghg_agent.domain.mapping import MapperConfig, map_fields
from ghg_agent.domain.models import (
    CanonicalField,
    ContractStatus,
    DeliveryResult,
    IngressBodyType,
    IngressResult,
    MappingResult,
    ProfileResult,
    RunStatus,
    SourceProfile,
    TransformResult,
    ValidationResult,
    ValidationVerdict,
    assert_transition,
)
from ghg_agent.domain.normalization import NormalizationError, normalize_payload
from ghg_agent.domain.profiling import profile_payload
from ghg_agent.domain.validation import ValidationConfig, validate_mapping_result
from ghg_agent.evidence import EvidenceError, EvidenceWriter
from ghg_agent.governance import GovernanceAuthorityContext, build_context
from ghg_agent.governance.candidate_scope import load_candidate_inventory
from ghg_agent.llm.client import LLMClient, MockLLMClient
from ghg_agent.reference.lookup import ReferenceLookup


class PipelineState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    correlation_id: str
    status: RunStatus = RunStatus.RECEIVED
    ingress: IngressResult | None = None
    business: dict[str, Any] | None = None
    profile_result: ProfileResult | None = None
    fields: list[CanonicalField] = Field(default_factory=list)
    mapping_result: MappingResult | None = None
    validation_result: ValidationResult | None = None
    transform_result: TransformResult | None = None
    delivery_result: DeliveryResult | None = None
    error: str | None = None
    trace: list[dict[str, Any]] = Field(default_factory=list)


@dataclass
class Pipeline:
    settings: Settings
    reference: ReferenceLookup
    skill: ImoMappingSkillAdapter
    llm_client: LLMClient
    governance: GovernanceAuthorityContext
    candidate_scope: frozenset[str] | None = None
    mcp_mode: str = "off"

    def __post_init__(self) -> None:
        self._graph = self._build_graph()

    # --- 상태 전이 ---

    def _advance(self, state: PipelineState, target: RunStatus, agent: str) -> None:
        assert_transition(state.status, target)
        state.trace.append(
            {
                "agent": agent,
                "from": state.status.value,
                "to": target.value,
                "at": datetime.now(UTC).isoformat(),
            }
        )
        state.status = target

    # --- 노드 ---

    def _node_profile(self, state: PipelineState) -> PipelineState:
        if state.ingress is None or state.business is None:
            state.error = "INGRESS_MISSING"
            self._advance(state, RunStatus.FAILED, "DataProfilerAgent")
            return state
        # Governance: CandidateSet/Reference Authority 미승인 시 매핑 파이프라인 자체
        # 진입을 차단한다(fail-closed). RECEIVED 단계에서 검사해 정규화도 하지 않는다.
        if not self.governance.candidate_mapping_eligible:
            state.error = "GOVERNANCE_CANDIDATE_MAPPING_BLOCKED"
            self._advance(state, RunStatus.REVIEW_REQUIRED, "OrchestratorAgent")
            return state
        if state.ingress.body_type != IngressBodyType.RAW_JSON_BODY:
            state.error = f"UNSUPPORTED_BODY_TYPE:{state.ingress.body_type.value}"
            self._advance(state, RunStatus.REVIEW_REQUIRED, "DataProfilerAgent")
            return state
        result = profile_payload(state.business)
        state.profile_result = result
        if result.selected_profile == SourceProfile.UNKNOWN:
            state.error = "PROFILE_UNKNOWN"
            self._advance(state, RunStatus.REVIEW_REQUIRED, "DataProfilerAgent")
            return state
        self._advance(state, RunStatus.PROFILED, "DataProfilerAgent")
        try:
            state.fields = normalize_payload(state.business, result.selected_profile)
        except NormalizationError as error:
            # DEFECT-1: 과도한 중첩 등 정규화 실패는 fail-closed(REVIEW_REQUIRED).
            state.error = f"NORMALIZATION_{error.code}"
            self._advance(state, RunStatus.REVIEW_REQUIRED, "DataProfilerAgent")
            return state
        self._advance(state, RunStatus.NORMALIZED, "DataProfilerAgent")
        return state

    def _node_map(self, state: PipelineState) -> PipelineState:
        assert state.profile_result is not None  # graph 순서상 보장
        self._advance(state, RunStatus.MAPPING_REQUESTED, "IMOMapperAgent")
        try:
            state.mapping_result = map_fields(
                state.fields,
                state.profile_result.selected_profile,
                self.reference,
                self.skill,
                self.llm_client,
                MapperConfig(
                    confidence_threshold=self.settings.mapping_confidence_threshold,
                    candidate_scope=self.candidate_scope,
                ),
                state.correlation_id,
            )
        except Exception as error:
            state.error = f"MAPPING_ERROR:{type(error).__name__}"
            self._advance(state, RunStatus.FAILED, "IMOMapperAgent")
            return state
        self._advance(state, RunStatus.MAPPED, "IMOMapperAgent")
        return state

    def _node_validate(self, state: PipelineState) -> PipelineState:
        assert state.mapping_result is not None  # graph 순서상 보장
        validation = validate_mapping_result(
            state.mapping_result,
            state.fields,
            self.reference,
            self.skill,
            ValidationConfig(
                confidence_threshold=self.settings.mapping_confidence_threshold
            ),
        )
        state.validation_result = validation
        unmapped = state.mapping_result.metrics.get("unmapped", 0)
        if validation.overall in (ValidationVerdict.PASS, ValidationVerdict.WARNING) and not unmapped:
            self._advance(state, RunStatus.VALIDATED, "MappingValidationAgent")
        else:
            state.error = f"VALIDATION_{validation.overall.value}" + (
                f"; unmapped={unmapped}" if unmapped else ""
            )
            self._advance(state, RunStatus.REVIEW_REQUIRED, "MappingValidationAgent")
        return state

    def _node_transform(self, state: PipelineState) -> PipelineState:
        assert state.mapping_result is not None and state.validation_result is not None
        try:
            state.transform_result = transform(
                state.mapping_result,
                state.fields,
                state.validation_result,
                state.correlation_id,
            )
        except Exception as error:
            state.error = f"TRANSFORM_ERROR:{type(error).__name__}"
            self._advance(state, RunStatus.FAILED, "KRGearsTransformationAgent")
            return state
        self._advance(state, RunStatus.TRANSFORMED, "KRGearsTransformationAgent")
        return state

    def _node_deliver(self, state: PipelineState) -> PipelineState:
        assert state.transform_result is not None  # graph 순서상 보장
        self._advance(state, RunStatus.DELIVERY_REQUESTED, "DeliveryAdapter")
        # Governance: DeliveryAuthority 미승인 시 실제(http) delivery 차단.
        mode = self.settings.kr_gears_delivery_mode
        if mode == "http" and not self.governance.kr_gears_actual_delivery_allowed:
            result = DeliveryResult(
                correlation_id=state.correlation_id, mode="http", real_call=False,
                status="BLOCKED", detail="GOVERNANCE_DELIVERY_NOT_ALLOWED",
            )
        else:
            result = deliver(state.transform_result, mode, self.settings.kr_gears_api_url)
        state.delivery_result = result
        if result.status == "DELIVERED":
            # 최종 DELIVERED(권위) 는 executable_mapping_eligible + delivery 승인 +
            # 실제 contract 검증을 모두 요구한다. 하나라도 불충족이면 REVIEW_REQUIRED.
            contract_ok = state.transform_result.contract_status == ContractStatus.CONTRACT_VERIFIED
            if (
                contract_ok
                and self.governance.executable_mapping_eligible
                and self.governance.kr_gears_actual_delivery_allowed
            ):
                self._advance(state, RunStatus.DELIVERED, "DeliveryAdapter")
            elif not contract_ok:
                # PROVISIONAL contract 는 성공으로 위장하지 않는다 → REVIEW_REQUIRED
                state.error = "KR_GEARS_CONTRACT_PROVISIONAL"
                self._advance(state, RunStatus.REVIEW_REQUIRED, "DeliveryAdapter")
            else:
                state.error = "GOVERNANCE_EXECUTABLE_MAPPING_BLOCKED"
                self._advance(state, RunStatus.REVIEW_REQUIRED, "DeliveryAdapter")
        elif result.status == "BLOCKED":
            state.error = "DELIVERY_BLOCKED_PROVISIONAL_CONTRACT"
            self._advance(state, RunStatus.REVIEW_REQUIRED, "DeliveryAdapter")
        else:
            state.error = f"DELIVERY_FAILED:{result.detail}"
            self._advance(state, RunStatus.FAILED, "DeliveryAdapter")
        return state

    # --- 그래프 ---

    def _build_graph(self):
        builder = StateGraph(PipelineState)
        builder.add_node("profile", self._node_profile)
        builder.add_node("map", self._node_map)
        builder.add_node("validate", self._node_validate)
        builder.add_node("transform", self._node_transform)
        builder.add_node("deliver", self._node_deliver)

        builder.add_edge(START, "profile")
        builder.add_conditional_edges(
            "profile",
            lambda s: "map" if s.status == RunStatus.NORMALIZED else END,
            {"map": "map", END: END},
        )
        builder.add_conditional_edges(
            "map",
            lambda s: "validate" if s.status == RunStatus.MAPPED else END,
            {"validate": "validate", END: END},
        )
        builder.add_conditional_edges(
            "validate",
            lambda s: "transform" if s.status == RunStatus.VALIDATED else END,
            {"transform": "transform", END: END},
        )
        builder.add_conditional_edges(
            "transform",
            lambda s: "deliver" if s.status == RunStatus.TRANSFORMED else END,
            {"deliver": "deliver", END: END},
        )
        builder.add_edge("deliver", END)
        return builder.compile()

    # --- 실행 ---

    def run(
        self,
        raw: bytes,
        content_type: str | None,
        correlation_id: str | None = None,
    ) -> PipelineState:
        ingress, business = ingest(
            raw, content_type, correlation_id,
            limits=ResourceLimits(
                max_node_count=self.settings.max_node_count,
                max_array_length=self.settings.max_array_length,
                max_field_count=self.settings.max_field_count,
                max_scalar_text_length=self.settings.max_scalar_text_length,
            ),
        )

        # DEFECT-1b: idempotency 는 manifest 가 아니라 실행 디렉터리 존재로 판정한다.
        # 부분(크래시)·완료·진행중 어떤 경우든 동일 correlation_id 재사용은 conflict.
        evidence_dir = self.settings.audit_log_dir / ingress.correlation_id
        if evidence_dir.exists() and any(evidence_dir.iterdir()):
            raise DuplicateRunError(ingress.correlation_id)

        try:
            writer = EvidenceWriter(self.settings.audit_log_dir, ingress.correlation_id)
        except EvidenceError as error:
            raise DuplicateRunError(ingress.correlation_id) from error

        writer.write_bytes("raw-input.json", raw)
        writer.write_text("raw-input.sha256", ingress.raw_sha256 + "\n")

        state = PipelineState(correlation_id=ingress.correlation_id)
        state.ingress = ingress
        state.business = business
        state.trace.append(
            {
                "agent": "IngressAgent",
                "from": None,
                "to": RunStatus.RECEIVED.value,
                "at": datetime.now(UTC).isoformat(),
            }
        )

        # DEFECT-1b: 어떤 stage 예외에도 evidence 를 FAILED 로 반드시 완결한다
        # (부분 evidence + 매니페스트 부재로 인한 cid 오염 방지, fail-closed).
        try:
            if ingress.validation_errors:
                state.error = ";".join(ingress.validation_errors)
                self._advance(state, RunStatus.REVIEW_REQUIRED, "IngressAgent")
                final = state
            else:
                result = self._graph.invoke(state)
                final = PipelineState.model_validate(result)
        except Exception as error:
            if state.status not in (RunStatus.REVIEW_REQUIRED, RunStatus.FAILED):
                state.error = f"PIPELINE_EXCEPTION:{type(error).__name__}"
                self._advance(state, RunStatus.FAILED, "OrchestratorAgent")
            final = state

        self._write_evidence(writer, final)
        return final

    def _write_evidence(self, writer: EvidenceWriter, state: PipelineState) -> None:
        assert state.ingress is not None
        writer.write_json("governance-context.json", self.governance.snapshot())
        writer.write_json("ingress-result.json", state.ingress.model_dump(mode="json"))
        if state.profile_result is not None:
            writer.write_json("profile-result.json", state.profile_result.model_dump(mode="json"))
        if state.fields:
            writer.write_json(
                "normalized-input.json", [f.model_dump(mode="json") for f in state.fields]
            )
        writer.write_json("agent-trace.json", state.trace)
        writer.write_json("skill-calls.json", self.skill.drain_call_log())
        writer.write_json("llm-calls.json", self.llm_client.drain_call_log())
        writer.write_json(
            "mcp-calls.json",
            {"mode": self.mcp_mode, "calls": []} if self.mcp_mode == "off" else {"mode": self.mcp_mode},
        )
        if state.mapping_result is not None:
            writer.write_json("mapping-result.json", state.mapping_result.model_dump(mode="json"))
        if state.validation_result is not None:
            writer.write_json(
                "validation-result.json", state.validation_result.model_dump(mode="json")
            )
        if state.transform_result is not None:
            writer.write_json(
                "kr-gears-output.json", state.transform_result.model_dump(mode="json")
            )
        if state.delivery_result is not None:
            writer.write_json(
                "delivery-result.json", state.delivery_result.model_dump(mode="json")
            )
        writer.write_text("summary.md", self._summary_markdown(state))
        writer.finalize_manifest(
            source_type="synthetic_fixture" if self.settings.synthetic_data else "external",
            synthetic_data=self.settings.synthetic_data,
            reference_model_version=(
                state.mapping_result.reference_model_version if state.mapping_result else None
            ),
            validator_version=self.skill.skill_version(),
            llm_provider=self.llm_client.provider,
            llm_model=getattr(self.llm_client, "model", "") or "",
            mcp_real_or_mock="off" if self.mcp_mode == "off" else self.mcp_mode,
            skill_real_or_mock="real" if self.skill.real_call else "mock",
            kr_gears_contract_status=(
                state.transform_result.contract_status.value
                if state.transform_result
                else "NOT_TRANSFORMED"
            ),
            final_status=state.status.value,
            project_root=PROJECT_ROOT,
            governance_flags=self.governance.flags(),
        )

    def _summary_markdown(self, state: PipelineState) -> str:
        lines = [
            f"# Run {state.correlation_id}",
            "",
            f"- final_status: **{state.status.value}**",
            f"- error: {state.error or '-'}",
            f"- profile: {state.profile_result.selected_profile.value if state.profile_result else '-'}",
        ]
        if state.mapping_result:
            lines.append(f"- metrics: {state.mapping_result.metrics}")
        if state.validation_result:
            v = state.validation_result
            lines.append(
                f"- validation: overall={v.overall.value} "
                f"pass={v.pass_count} warn={v.warning_count} fail={v.fail_count} "
                f"not_verified={v.not_verified_count}"
            )
        if state.transform_result:
            lines.append(f"- kr_gears_contract_status: {state.transform_result.contract_status.value}")
        if state.delivery_result:
            lines.append(
                f"- delivery: {state.delivery_result.status} (real={state.delivery_result.real_call})"
            )
        return "\n".join(lines) + "\n"


class DuplicateRunError(Exception):
    def __init__(self, correlation_id: str) -> None:
        super().__init__(f"correlation_id {correlation_id} 는 이미 실행되었다")
        self.correlation_id = correlation_id


def build_pipeline(settings: Settings, llm_client: LLMClient | None = None) -> Pipeline:
    reference = ReferenceLookup(
        registry_db_path=settings.registry_db_path,
        version="FAL50",
        alias_config_path=settings.alias_config_path,
        code_lists_path=settings.code_lists_path,
    )
    skill = ImoMappingSkillAdapter(
        skill_path=settings.imo_mapping_skill_path,
        registry_db_path=settings.registry_db_path,
        timeout_seconds=settings.skill_timeout_seconds,
    )
    # Governance Runtime Binding — reference/candidate-set 준비 여부로 Authority 바인딩.
    reference_ready = settings.registry_db_path.is_file()
    skill_readiness = skill.readiness()
    # F-STEP7-2: 승인 후보 집합 로드 (부재/hash 오류 시 UNBOUND → candidate_mapping_eligible false)
    inventory = load_candidate_inventory(settings.candidate_inventory_path)
    governance = build_context(
        settings,
        reference_ready=reference_ready and bool(skill_readiness.get("registry_versions")),
        candidate_set_ready=bool(skill_readiness.get("ready")),
        validator_version=skill_readiness.get("skill_version"),
        candidate_inventory=inventory,
    )
    return Pipeline(
        settings=settings,
        reference=reference,
        skill=skill,
        llm_client=llm_client or MockLLMClient(),
        governance=governance,
        candidate_scope=inventory.ids if inventory.bound else None,
        mcp_mode=settings.mcp_mode,
    )
