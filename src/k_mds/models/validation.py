"""검증 결과 Contract 모델 (AGENTS.md §10).

PASS, WARNING, FAIL 상태 불변조건과 Finding-Evidence 추적성을
Pydantic model_validator로 강제한다. 직렬화 시 AGENTS.md §10 JSON 예시와
동일한 camelCase Alias를 사용한다 (예: human_review_required -> humanReviewRequired).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class ResultStatus(StrEnum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class FindingSeverity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"


class DataClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"


#: Finding.actual_value 로깅 정책 선언 (AGENTS.md §10 finding_value_policy).
#: 이번 단계에서는 정책 Contract만 정의하며 자동 마스킹·Hash 처리는 구현하지 않는다.
FINDING_VALUE_POLICY: dict[DataClassification, str] = {
    DataClassification.PUBLIC: "raw_value_allowed",
    DataClassification.INTERNAL: "masked_value_only",
    DataClassification.CONFIDENTIAL: "hash_only",
    DataClassification.SECRET: "never_log",
}


class _ContractModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class Evidence(_ContractModel):
    evidence_id: str = Field(min_length=1)
    fal_version: str = Field(min_length=1)
    ontology_version: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    resource_uri: str | None = None
    source_file: str | None = None
    source_hash: str | None = None


class ValidationFinding(_ContractModel):
    severity: FindingSeverity
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    related_rule_ids: list[str] = Field(default_factory=list)
    path: str | None = None
    # actual_value는 선택값이며 데이터 분류에 따라 FINDING_VALUE_POLICY를 적용해야 한다.
    actual_value: str | None = None
    expected: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class SkillResult(_ContractModel):
    status: ResultStatus
    human_review_required: bool
    data: dict[str, Any] = Field(default_factory=dict)
    errors: list[ValidationFinding] = Field(default_factory=list)
    warnings: list[ValidationFinding] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enforce_severity_segregation(self) -> SkillResult:
        for finding in self.errors:
            if finding.severity is not FindingSeverity.ERROR:
                raise ValueError(
                    f"errors에는 ERROR severity만 허용된다 (발견: {finding.severity.value})"
                )
        for finding in self.warnings:
            if finding.severity is not FindingSeverity.WARNING:
                raise ValueError(
                    f"warnings에는 WARNING severity만 허용된다 (발견: {finding.severity.value})"
                )
        return self

    @model_validator(mode="after")
    def _enforce_status_invariants(self) -> SkillResult:
        if self.status is ResultStatus.PASS:
            if self.errors:
                raise ValueError("PASS 결과는 Error를 포함할 수 없다")
            if self.warnings:
                raise ValueError("PASS 결과는 Warning을 포함할 수 없다")
            if self.human_review_required:
                raise ValueError("PASS 결과는 human_review_required=false여야 한다")
        elif self.status is ResultStatus.WARNING:
            if self.errors:
                raise ValueError("WARNING 결과는 Error를 포함할 수 없다")
            if not self.warnings:
                raise ValueError("WARNING 결과는 최소 1개의 Warning이 필요하다")
            if not self.human_review_required:
                raise ValueError("WARNING 결과는 human_review_required=true여야 한다")
        else:
            if not self.errors:
                raise ValueError("FAIL 결과는 최소 1개의 Error가 필요하다")
            if not self.human_review_required:
                raise ValueError("FAIL 결과는 human_review_required=true여야 한다")
        return self

    @model_validator(mode="after")
    def _enforce_evidence_integrity(self) -> SkillResult:
        evidence_ids = [item.evidence_id for item in self.evidence]
        duplicates = sorted({eid for eid in evidence_ids if evidence_ids.count(eid) > 1})
        if duplicates:
            raise ValueError(f"중복 evidence_id는 허용되지 않는다: {duplicates}")

        known_ids = set(evidence_ids)
        for finding in [*self.errors, *self.warnings]:
            dangling = [ref for ref in finding.evidence_refs if ref not in known_ids]
            if dangling:
                raise ValueError(
                    f"Finding({finding.code})이 존재하지 않는 evidence_id를 참조한다: {dangling}"
                )
        return self
