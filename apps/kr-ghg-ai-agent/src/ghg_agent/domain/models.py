"""Typed domain models (Pydantic v2, extra=forbid).

Agent 간 통신은 전부 이 모델을 통해서만 이뤄진다 (D-2).
LLM 후보는 최종 매핑 필드에 직접 기록되지 않는다 (C-6) —
candidate_list 에만 존재하며 validator 통과 시에만 승격된다.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- 상태 기계 (A-1) ---

class RunStatus(StrEnum):
    RECEIVED = "RECEIVED"
    PROFILED = "PROFILED"
    NORMALIZED = "NORMALIZED"
    MAPPING_REQUESTED = "MAPPING_REQUESTED"
    MAPPED = "MAPPED"
    VALIDATED = "VALIDATED"
    TRANSFORMED = "TRANSFORMED"
    DELIVERY_REQUESTED = "DELIVERY_REQUESTED"
    DELIVERED = "DELIVERED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"


#: 허용 전이 — 이 표에 없는 전이는 거부된다.
ALLOWED_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.RECEIVED: frozenset({RunStatus.PROFILED, RunStatus.REVIEW_REQUIRED, RunStatus.FAILED}),
    RunStatus.PROFILED: frozenset({RunStatus.NORMALIZED, RunStatus.REVIEW_REQUIRED, RunStatus.FAILED}),
    RunStatus.NORMALIZED: frozenset({RunStatus.MAPPING_REQUESTED, RunStatus.FAILED}),
    RunStatus.MAPPING_REQUESTED: frozenset({RunStatus.MAPPED, RunStatus.REVIEW_REQUIRED, RunStatus.FAILED}),
    RunStatus.MAPPED: frozenset({RunStatus.VALIDATED, RunStatus.REVIEW_REQUIRED, RunStatus.FAILED}),
    RunStatus.VALIDATED: frozenset({RunStatus.TRANSFORMED, RunStatus.REVIEW_REQUIRED, RunStatus.FAILED}),
    RunStatus.TRANSFORMED: frozenset({RunStatus.DELIVERY_REQUESTED, RunStatus.REVIEW_REQUIRED, RunStatus.FAILED}),
    RunStatus.DELIVERY_REQUESTED: frozenset({RunStatus.DELIVERED, RunStatus.REVIEW_REQUIRED, RunStatus.FAILED}),
    RunStatus.DELIVERED: frozenset(),
    RunStatus.REVIEW_REQUIRED: frozenset(),
    RunStatus.FAILED: frozenset(),
}


class InvalidTransition(Exception):
    pass


def assert_transition(current: RunStatus, target: RunStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransition(f"{current.value} -> {target.value} 전이는 허용되지 않는다")


# --- 입력 / 프로파일 (A-2, A-3) ---

class IngressBodyType(StrEnum):
    KNOWN_ENVELOPE = "KNOWN_ENVELOPE"
    RAW_JSON_BODY = "RAW_JSON_BODY"
    FILE_PAYLOAD = "FILE_PAYLOAD"
    FILE_REFERENCE = "FILE_REFERENCE"
    UNKNOWN = "UNKNOWN"


class SourceProfile(StrEnum):
    VESSEL_PERFORMANCE = "VESSEL_PERFORMANCE"
    NOON_REPORT = "NOON_REPORT"
    EVENT_REPORT = "EVENT_REPORT"
    UNKNOWN = "UNKNOWN"


class IngressResult(StrictModel):
    correlation_id: str
    body_type: IngressBodyType
    content_type: str | None = None
    raw_sha256: str
    payload_bytes: int
    transport_metadata: dict[str, Any] = Field(default_factory=dict)
    dataset_metadata: dict[str, Any] = Field(default_factory=dict)
    validation_errors: list[str] = Field(default_factory=list)


class CanonicalField(StrictModel):
    source_path: str
    source_name: str
    normalized_name: str
    description: str | None = None
    value: Any = None
    unit: str | None = None
    data_type: str | None = None
    timestamp: str | None = None
    equipment_context: str | None = None
    vessel_context: str | None = None
    voyage_context: str | None = None
    report_context: str | None = None


class ProfileResult(StrictModel):
    selected_profile: SourceProfile
    confidence: float = Field(ge=0.0, le=1.0)
    deterministic_evidence: list[str] = Field(default_factory=list)
    competing_profiles: list[str] = Field(default_factory=list)
    classification_method: str = "deterministic_marker"


# --- 매핑 (A-4) ---

class MappingMethod(StrEnum):
    EXPLICIT_IDENTIFIER_VALIDATED = "EXPLICIT_IDENTIFIER_VALIDATED"
    EXACT_REFERENCE = "EXACT_REFERENCE"
    NORMALIZED_EXACT_REFERENCE = "NORMALIZED_EXACT_REFERENCE"
    ALIAS_REFERENCE = "ALIAS_REFERENCE"
    SKILL_RULE = "SKILL_RULE"
    LLM_SUGGESTED_AND_VALIDATED = "LLM_SUGGESTED_AND_VALIDATED"
    UNMAPPED = "UNMAPPED"


class MappingCandidate(StrictModel):
    imo_data_number: str
    source: str  # skill | llm | reference
    confidence: float | None = None
    reason: str | None = None
    validator_status: str | None = None  # PASS | WARNING | FAIL | NOT_VERIFIED


class FieldMapping(StrictModel):
    source_path: str
    source_name: str
    normalized_name: str
    source_value_type: str | None = None
    source_unit: str | None = None
    imo_data_number: str | None = None
    imo_data_element_name: str | None = None
    reference_model_version: str | None = None
    confidence: float | None = None
    mapping_method: MappingMethod = MappingMethod.UNMAPPED
    candidate_list: list[MappingCandidate] = Field(default_factory=list)
    validator_status: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MappingResult(StrictModel):
    correlation_id: str
    profile: SourceProfile
    reference_model_version: str
    fields: list[FieldMapping] = Field(default_factory=list)
    metrics: dict[str, int] = Field(default_factory=dict)


# --- 검증 (A-5) ---

class ValidationVerdict(StrEnum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_VERIFIED = "NOT_VERIFIED"


class ValidationItem(StrictModel):
    source_path: str
    imo_data_number: str | None = None
    check: str
    verdict: ValidationVerdict
    code: str | None = None
    message: str | None = None


class ValidationResult(StrictModel):
    correlation_id: str
    overall: ValidationVerdict
    items: list[ValidationItem] = Field(default_factory=list)
    pass_count: int = 0
    warning_count: int = 0
    fail_count: int = 0
    not_verified_count: int = 0


# --- 변환 (A-6) ---

class ContractStatus(StrEnum):
    CONTRACT_VERIFIED = "CONTRACT_VERIFIED"
    PROVISIONAL = "PROVISIONAL"


class FieldProvenance(StrictModel):
    target_path: str
    source_path: str
    source_value_hash: str | None = None
    imo_data_number: str | None = None
    transformation_rule_id: str
    transformation_rule_version: str
    original_unit: str | None = None
    target_unit: str | None = None
    conversion_applied: bool = False
    contract_status: ContractStatus


class TransformResult(StrictModel):
    correlation_id: str
    profile: SourceProfile
    contract_status: ContractStatus
    payload: dict[str, Any]
    provenance: list[FieldProvenance] = Field(default_factory=list)
    verdict_report: dict[str, Any] | None = None  # 실계약 KrGearsReport (검증됨)
    warnings: list[str] = Field(default_factory=list)


class DeliveryResult(StrictModel):
    correlation_id: str
    mode: str  # mock | http
    real_call: bool
    status: str  # DELIVERED | BLOCKED | FAILED
    detail: str | None = None
