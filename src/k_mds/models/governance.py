"""Governance Decision 모델 (ADR-0004).

SkillResult는 Low-level Skill 실행 결과이고, GovernanceResult는 표준·Mapping·
규제 관련 최종 Governance Decision이다. 두 Contract는 Evidence 요구조건이
다르다 — Technical Failure에는 Evidence를 강제하지 않지만, Governance
Decision에는 Evidence가 최소 1개 반드시 존재해야 한다.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from k_mds.models.validation import (
    Evidence,
    FindingSeverity,
    ResultStatus,
    SkillResult,
    ValidationFinding,
)


class GovernanceDecisionStatus(StrEnum):
    """Governance Decision 상태 — Execution PASS/FAIL(ResultStatus)과 의미가 다르다."""

    APPROVED = "APPROVED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECTED = "REJECTED"


class GovernanceDecisionType(StrEnum):
    DATASET = "DATASET"
    DATA_ELEMENT = "DATA_ELEMENT"
    ELEMENT_OCCURRENCE = "ELEMENT_OCCURRENCE"
    MAPPING = "MAPPING"
    BUSINESS_RULE = "BUSINESS_RULE"
    DATA_QUALITY = "DATA_QUALITY"


class GovernanceResult(BaseModel):
    """Evidence가 필수인 최종 Governance Decision Contract."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )

    decision_id: str = Field(min_length=1)
    decision_type: GovernanceDecisionType
    status: GovernanceDecisionStatus
    subject_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    evidence: list[Evidence] = Field(min_length=1)
    findings: list[ValidationFinding] = Field(default_factory=list)
    # Low-level 실행 증적이며 Evidence 요구조건을 대신하지 않는다.
    source_results: list[SkillResult] = Field(default_factory=list)
    human_review_required: bool

    @model_validator(mode="after")
    def _enforce_decision_invariants(self) -> GovernanceResult:
        error_findings = [
            finding
            for finding in self.findings
            if finding.severity is FindingSeverity.ERROR
        ]

        if self.status is GovernanceDecisionStatus.APPROVED:
            if self.human_review_required:
                raise ValueError("APPROVED 결정은 human_review_required=false여야 한다")
            if error_findings:
                raise ValueError("APPROVED 결정은 ERROR severity Finding을 포함할 수 없다")
            if any(
                result.status is ResultStatus.FAIL for result in self.source_results
            ):
                raise ValueError("APPROVED 결정은 FAIL source_result를 포함할 수 없다")
        elif self.status is GovernanceDecisionStatus.REVIEW_REQUIRED:
            if not self.human_review_required:
                raise ValueError("REVIEW_REQUIRED 결정은 human_review_required=true여야 한다")
            if not self.findings:
                raise ValueError("REVIEW_REQUIRED 결정은 최소 1개의 Finding이 필요하다")
        else:
            if not self.human_review_required:
                raise ValueError("REJECTED 결정은 human_review_required=true여야 한다")
            if not error_findings:
                raise ValueError("REJECTED 결정은 최소 1개의 ERROR Finding이 필요하다")
        return self

    @model_validator(mode="after")
    def _enforce_evidence_integrity(self) -> GovernanceResult:
        evidence_ids = [item.evidence_id for item in self.evidence]
        duplicates = sorted({eid for eid in evidence_ids if evidence_ids.count(eid) > 1})
        if duplicates:
            raise ValueError(f"중복 evidence_id는 허용되지 않는다: {duplicates}")

        known_ids = set(evidence_ids)
        for finding in self.findings:
            dangling = [ref for ref in finding.evidence_refs if ref not in known_ids]
            if dangling:
                raise ValueError(
                    f"Finding({finding.code})이 존재하지 않는 evidence_id를 참조한다: {dangling}"
                )
        return self
