"""SkillResult 상태 불변조건 및 Evidence 추적성 Contract Test (AGENTS.md §10).

모든 Fixture 값은 가상임이 드러나는 TEST 표기를 사용한다.
실제 IMO ID, Technical Position, Rule 또는 Code Value를 생성하지 않는다.
"""

import pytest
from pydantic import ValidationError

from k_mds.models import (
    Evidence,
    FindingSeverity,
    ResultStatus,
    SkillResult,
    ValidationFinding,
)

ERROR = FindingSeverity.ERROR
WARN = FindingSeverity.WARNING


def make_evidence(evidence_id: str = "ev-test-001") -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        fal_version="FALTEST",
        ontology_version="0.0.0-test",
        profile_version="kr-ghg-0.0.0-test",
        resource_uri="imo://elements/TEST-ELEMENT-001",
    )


def make_finding(
    severity: FindingSeverity, evidence_refs: list[str] | None = None
) -> ValidationFinding:
    return ValidationFinding(
        severity=severity,
        code="VAL_TEST_001",
        message="테스트용 가상 Finding이다.",
        rule_id="urn:test:rule:contract:0.0.1",
        evidence_refs=evidence_refs or [],
    )


# --- PASS 불변조건 (지시 Test 1~3) ---


def test_pass_with_error_raises() -> None:
    with pytest.raises(ValidationError):
        SkillResult(
            status=ResultStatus.PASS,
            human_review_required=False,
            errors=[make_finding(ERROR)],
        )


def test_pass_with_warning_raises() -> None:
    with pytest.raises(ValidationError):
        SkillResult(
            status=ResultStatus.PASS,
            human_review_required=False,
            warnings=[make_finding(WARN)],
        )


def test_pass_with_human_review_required_raises() -> None:
    with pytest.raises(ValidationError):
        SkillResult(status=ResultStatus.PASS, human_review_required=True)


# --- WARNING 불변조건 (지시 Test 4~6) ---


def test_warning_without_warnings_raises() -> None:
    with pytest.raises(ValidationError):
        SkillResult(status=ResultStatus.WARNING, human_review_required=True)


def test_warning_with_error_raises() -> None:
    with pytest.raises(ValidationError):
        SkillResult(
            status=ResultStatus.WARNING,
            human_review_required=True,
            errors=[make_finding(ERROR)],
            warnings=[make_finding(WARN)],
        )


def test_warning_without_human_review_raises() -> None:
    with pytest.raises(ValidationError):
        SkillResult(
            status=ResultStatus.WARNING,
            human_review_required=False,
            warnings=[make_finding(WARN)],
        )


# --- FAIL 불변조건 (지시 Test 7~8) ---


def test_fail_without_errors_raises() -> None:
    with pytest.raises(ValidationError):
        SkillResult(status=ResultStatus.FAIL, human_review_required=True)


def test_fail_without_human_review_raises() -> None:
    with pytest.raises(ValidationError):
        SkillResult(
            status=ResultStatus.FAIL,
            human_review_required=False,
            errors=[make_finding(ERROR)],
        )


# --- Severity 분리 (지시 Test 9~10) ---


def test_warning_severity_inside_errors_raises() -> None:
    with pytest.raises(ValidationError):
        SkillResult(
            status=ResultStatus.FAIL,
            human_review_required=True,
            errors=[make_finding(WARN)],
        )


def test_error_severity_inside_warnings_raises() -> None:
    with pytest.raises(ValidationError):
        SkillResult(
            status=ResultStatus.WARNING,
            human_review_required=True,
            warnings=[make_finding(ERROR)],
        )


# --- Evidence 추적성 (지시 Test 11~12) ---


def test_dangling_evidence_ref_raises() -> None:
    with pytest.raises(ValidationError):
        SkillResult(
            status=ResultStatus.FAIL,
            human_review_required=True,
            errors=[make_finding(ERROR, evidence_refs=["ev-test-missing"])],
            evidence=[make_evidence("ev-test-001")],
        )


def test_duplicate_evidence_id_raises() -> None:
    with pytest.raises(ValidationError):
        SkillResult(
            status=ResultStatus.PASS,
            human_review_required=False,
            evidence=[make_evidence("ev-test-dup"), make_evidence("ev-test-dup")],
        )


# --- 유효 결과 생성 (지시 Test 13) ---


def test_valid_pass_result() -> None:
    result = SkillResult(
        status=ResultStatus.PASS,
        human_review_required=False,
        evidence=[make_evidence()],
    )
    assert result.status is ResultStatus.PASS
    assert result.errors == [] and result.warnings == []


def test_valid_warning_result() -> None:
    result = SkillResult(
        status=ResultStatus.WARNING,
        human_review_required=True,
        warnings=[make_finding(WARN, evidence_refs=["ev-test-001"])],
        evidence=[make_evidence("ev-test-001")],
    )
    assert result.status is ResultStatus.WARNING
    assert result.human_review_required is True


def test_camel_case_serialization_contract() -> None:
    # AGENTS.md §10 JSON 예시와 동일한 camelCase 직렬화 Contract를 검증한다.
    result = SkillResult(
        status=ResultStatus.PASS,
        human_review_required=False,
        evidence=[make_evidence()],
    )
    dumped = result.model_dump(by_alias=True)
    assert "humanReviewRequired" in dumped
    assert "human_review_required" not in dumped

    finding_dump = make_finding(ERROR, evidence_refs=["ev-test-001"]).model_dump(by_alias=True)
    assert "evidenceRefs" in finding_dump
    assert "evidence_refs" not in finding_dump


def test_valid_fail_result() -> None:
    result = SkillResult(
        status=ResultStatus.FAIL,
        human_review_required=True,
        errors=[make_finding(ERROR, evidence_refs=["ev-test-001"])],
        evidence=[make_evidence("ev-test-001")],
    )
    assert result.status is ResultStatus.FAIL
    assert len(result.errors) == 1
