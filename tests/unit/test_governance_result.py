"""GovernanceResult Contract Test (ADR-0004).

Governance Decision은 Evidence 최소 1개를 필수로 하며 상태 불변조건을
Pydantic으로 강제한다. 모든 Fixture는 TEST/FALTEST/urn:test 값만 사용한다.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from k_mds.models import (
    Evidence,
    FindingSeverity,
    GovernanceResult,
    ResultStatus,
    SkillResult,
    ValidationFinding,
)

EVIDENCE_ID = "evidence:TEST-SOURCE-001"


def make_evidence(evidence_id: str = EVIDENCE_ID) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        fal_version="FALTEST",
        ontology_version="0.0.0-test",
        profile_version="kr-profile-0.0.0-test",
        source_file="data/raw/FALTEST/test-source.xlsx",
        source_hash="TEST-SHA256-NOT-A-REAL-HASH",
        resource_uri="urn:test:source:001",
    )


def make_finding(
    severity: FindingSeverity, evidence_refs: list[str] | None = None
) -> ValidationFinding:
    return ValidationFinding(
        severity=severity,
        code="GOV_TEST_001",
        message="테스트용 가상 Finding이다.",
        rule_id="urn:test:rule:governance:0.0.1",
        evidence_refs=[EVIDENCE_ID] if evidence_refs is None else evidence_refs,
    )


def make_skill_result(status: ResultStatus) -> SkillResult:
    if status is ResultStatus.PASS:
        return SkillResult(status=status, human_review_required=False)
    if status is ResultStatus.WARNING:
        return SkillResult(
            status=status,
            human_review_required=True,
            warnings=[make_finding(FindingSeverity.WARNING, evidence_refs=[])],
        )
    return SkillResult(
        status=status,
        human_review_required=True,
        errors=[make_finding(FindingSeverity.ERROR, evidence_refs=[])],
    )


def make_payload(**overrides: object) -> dict[str, Any]:
    base: dict[str, Any] = {
        "decision_id": "TEST-DECISION-001",
        "decision_type": "DATA_ELEMENT",
        "status": "APPROVED",
        "subject_id": "TEST-ELEMENT-001",
        "summary": "테스트용 가상 Governance 요약이다.",
        "rationale": "테스트용 가상 근거다.",
        "evidence": [make_evidence()],
        "human_review_required": False,
    }
    base.update(overrides)
    return base


# --- 유효 생성 (지시 Test 1~3) ---


def test_valid_approved_result() -> None:
    result = GovernanceResult.model_validate(
        make_payload(source_results=[make_skill_result(ResultStatus.PASS)])
    )
    assert result.status.value == "APPROVED"


def test_valid_review_required_result() -> None:
    result = GovernanceResult.model_validate(
        make_payload(
            status="REVIEW_REQUIRED",
            human_review_required=True,
            findings=[make_finding(FindingSeverity.WARNING)],
        )
    )
    assert result.status.value == "REVIEW_REQUIRED"


def test_valid_rejected_result() -> None:
    result = GovernanceResult.model_validate(
        make_payload(
            status="REJECTED",
            human_review_required=True,
            findings=[make_finding(FindingSeverity.ERROR)],
            source_results=[make_skill_result(ResultStatus.FAIL)],
        )
    )
    assert result.status.value == "REJECTED"


# --- Evidence 필수 (지시 Test 4~6) ---


def test_approved_without_evidence_raises() -> None:
    with pytest.raises(ValidationError):
        GovernanceResult.model_validate(make_payload(evidence=[]))


def test_review_required_without_evidence_raises() -> None:
    with pytest.raises(ValidationError):
        GovernanceResult.model_validate(
            make_payload(
                status="REVIEW_REQUIRED",
                human_review_required=True,
                findings=[make_finding(FindingSeverity.WARNING, evidence_refs=[])],
                evidence=[],
            )
        )


def test_rejected_without_evidence_raises() -> None:
    with pytest.raises(ValidationError):
        GovernanceResult.model_validate(
            make_payload(
                status="REJECTED",
                human_review_required=True,
                findings=[make_finding(FindingSeverity.ERROR, evidence_refs=[])],
                evidence=[],
            )
        )


# --- APPROVED 불변조건 (지시 Test 7~9) ---


def test_approved_with_human_review_raises() -> None:
    with pytest.raises(ValidationError):
        GovernanceResult.model_validate(make_payload(human_review_required=True))


def test_approved_with_error_finding_raises() -> None:
    with pytest.raises(ValidationError):
        GovernanceResult.model_validate(
            make_payload(findings=[make_finding(FindingSeverity.ERROR)])
        )


def test_approved_with_fail_source_result_raises() -> None:
    with pytest.raises(ValidationError):
        GovernanceResult.model_validate(
            make_payload(source_results=[make_skill_result(ResultStatus.FAIL)])
        )


# --- REVIEW_REQUIRED 불변조건 (지시 Test 10~11) ---


def test_review_required_without_human_review_raises() -> None:
    with pytest.raises(ValidationError):
        GovernanceResult.model_validate(
            make_payload(
                status="REVIEW_REQUIRED",
                human_review_required=False,
                findings=[make_finding(FindingSeverity.WARNING)],
            )
        )


def test_review_required_without_findings_raises() -> None:
    with pytest.raises(ValidationError):
        GovernanceResult.model_validate(
            make_payload(status="REVIEW_REQUIRED", human_review_required=True, findings=[])
        )


# --- REJECTED 불변조건 (지시 Test 12~13) ---


def test_rejected_without_human_review_raises() -> None:
    with pytest.raises(ValidationError):
        GovernanceResult.model_validate(
            make_payload(
                status="REJECTED",
                human_review_required=False,
                findings=[make_finding(FindingSeverity.ERROR)],
            )
        )


def test_rejected_without_error_finding_raises() -> None:
    with pytest.raises(ValidationError):
        GovernanceResult.model_validate(
            make_payload(
                status="REJECTED",
                human_review_required=True,
                findings=[make_finding(FindingSeverity.WARNING)],
            )
        )


# --- Evidence 무결성 (지시 Test 14~15) ---


def test_duplicate_evidence_id_raises() -> None:
    with pytest.raises(ValidationError):
        GovernanceResult.model_validate(
            make_payload(evidence=[make_evidence(), make_evidence()])
        )


def test_dangling_evidence_ref_raises() -> None:
    with pytest.raises(ValidationError):
        GovernanceResult.model_validate(
            make_payload(
                status="REVIEW_REQUIRED",
                human_review_required=True,
                findings=[
                    make_finding(
                        FindingSeverity.WARNING,
                        evidence_refs=["evidence:TEST-MISSING-SOURCE"],
                    )
                ],
            )
        )


# --- Contract 경계와 직렬화 (지시 Test 16~20) ---


def test_extra_field_raises() -> None:
    with pytest.raises(ValidationError):
        GovernanceResult.model_validate(make_payload(unexpected_field="TEST"))


def test_camel_case_input_is_accepted() -> None:
    payload = {
        "decisionId": "TEST-DECISION-001",
        "decisionType": "DATA_ELEMENT",
        "status": "APPROVED",
        "subjectId": "TEST-ELEMENT-001",
        "summary": "테스트용 가상 Governance 요약이다.",
        "rationale": "테스트용 가상 근거다.",
        "evidence": [make_evidence()],
        "humanReviewRequired": False,
    }
    assert GovernanceResult.model_validate(payload).decision_id == "TEST-DECISION-001"


def test_alias_dump_contains_camel_case_keys() -> None:
    dumped = GovernanceResult.model_validate(make_payload()).model_dump(by_alias=True)
    for key in ("decisionId", "decisionType", "subjectId", "humanReviewRequired", "sourceResults"):
        assert key in dumped


def test_alias_dump_has_no_snake_case_keys() -> None:
    dumped = GovernanceResult.model_validate(make_payload()).model_dump(by_alias=True)
    for key in ("decision_id", "decision_type", "subject_id", "human_review_required",
                "source_results"):
        assert key not in dumped


def test_same_payload_produces_identical_dump() -> None:
    first = GovernanceResult.model_validate(make_payload()).model_dump(by_alias=True)
    second = GovernanceResult.model_validate(make_payload()).model_dump(by_alias=True)
    assert first == second
