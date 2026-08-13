"""governance_assemble Skill Contract Test (ADR-0005).

Assembler는 Governance 상태를 추론하지 않고, evidence_build 결과에서만
공식 Evidence를 수집한다. 모든 Fixture는 TEST/FALTEST/urn:test 값만 사용한다.
"""

from typing import Any

from k_mds.models import (
    Evidence,
    FindingSeverity,
    ResultStatus,
    SkillResult,
    ValidationFinding,
)
from k_mds.skills import governance_assemble

EVIDENCE_ID = "evidence:TEST-SOURCE-001"


def make_evidence(
    evidence_id: str = EVIDENCE_ID,
    source_hash: str = "TEST-SHA256-NOT-A-REAL-HASH",
    ontology_version: str = "0.0.0-test",
) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        fal_version="FALTEST",
        ontology_version=ontology_version,
        profile_version="kr-profile-0.0.0-test",
        source_file="data/raw/FALTEST/test-source.xlsx",
        source_hash=source_hash,
        resource_uri="urn:test:source:001",
    )


def make_evidence_result(*evidence: Evidence) -> SkillResult:
    return SkillResult(
        status=ResultStatus.PASS,
        human_review_required=False,
        evidence=list(evidence),
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


def make_source_result(status: ResultStatus) -> SkillResult:
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


def assemble(**overrides: Any) -> SkillResult:
    kwargs: dict[str, Any] = {
        "decision_id": "TEST-DECISION-001",
        "decision_type": "DATA_ELEMENT",
        "status": "APPROVED",
        "subject_id": "TEST-ELEMENT-001",
        "summary": "테스트용 가상 Governance 요약이다.",
        "rationale": "테스트용 가상 근거다.",
        "findings": [],
        "source_results": [make_source_result(ResultStatus.PASS)],
        "evidence_results": [make_evidence_result(make_evidence())],
        "human_review_required": False,
    }
    kwargs.update(overrides)
    return governance_assemble(**kwargs)


def assemble_review(**overrides: Any) -> SkillResult:
    base: dict[str, Any] = {
        "status": "REVIEW_REQUIRED",
        "human_review_required": True,
        "findings": [make_finding(FindingSeverity.WARNING)],
    }
    base.update(overrides)
    return assemble(**base)


def assemble_rejected(**overrides: Any) -> SkillResult:
    base: dict[str, Any] = {
        "status": "REJECTED",
        "human_review_required": True,
        "findings": [make_finding(FindingSeverity.ERROR)],
    }
    base.update(overrides)
    return assemble(**base)


# --- A. 성공 경로 (지시 Test 1~10) ---


def test_approved_assembly_succeeds() -> None:
    result = assemble()
    assert result.status is ResultStatus.PASS
    assert result.data["governanceStatus"] == "APPROVED"


def test_review_required_assembly_succeeds() -> None:
    result = assemble_review()
    assert result.status is ResultStatus.PASS
    assert result.data["governanceStatus"] == "REVIEW_REQUIRED"


def test_rejected_assembly_succeeds() -> None:
    result = assemble_rejected()
    assert result.status is ResultStatus.PASS
    assert result.data["governanceStatus"] == "REJECTED"


def test_all_statuses_return_outer_pass() -> None:
    for result in (assemble(), assemble_review(), assemble_rejected()):
        assert result.status is ResultStatus.PASS


def test_all_statuses_return_outer_no_human_review() -> None:
    for result in (assemble(), assemble_review(), assemble_rejected()):
        assert result.human_review_required is False
        assert result.errors == [] and result.warnings == []


def test_data_governance_status_matches_inner_result() -> None:
    for result in (assemble(), assemble_review(), assemble_rejected()):
        assert result.data["governanceStatus"] == result.data["governanceResult"]["status"]


def test_governance_result_dump_is_camel_case() -> None:
    dumped = assemble().data["governanceResult"]
    for key in ("decisionId", "decisionType", "subjectId", "humanReviewRequired", "sourceResults"):
        assert key in dumped
    assert "decision_id" not in dumped and "human_review_required" not in dumped


def test_outer_evidence_matches_inner_evidence() -> None:
    result = assemble()
    outer_ids = [item.evidence_id for item in result.evidence]
    inner_ids = [item["evidenceId"] for item in result.data["governanceResult"]["evidence"]]
    assert outer_ids == inner_ids == [EVIDENCE_ID]


def test_source_results_are_included_in_inner_result() -> None:
    result = assemble(source_results=[make_source_result(ResultStatus.PASS)])
    assert len(result.data["governanceResult"]["sourceResults"]) == 1


def test_source_result_evidence_is_not_promoted() -> None:
    other = SkillResult(
        status=ResultStatus.PASS,
        human_review_required=False,
        evidence=[make_evidence("evidence:TEST-OTHER-SOURCE")],
    )
    result = assemble(source_results=[other])
    assert [item.evidence_id for item in result.evidence] == [EVIDENCE_ID]


# --- B. Evidence 수집·병합 (지시 Test 11~20) ---


def test_identical_evidence_is_deduplicated() -> None:
    result = assemble(
        evidence_results=[
            make_evidence_result(make_evidence()),
            make_evidence_result(make_evidence()),
        ]
    )
    assert result.status is ResultStatus.PASS
    assert len(result.evidence) == 1


def test_same_id_different_hash_fails() -> None:
    result = assemble(
        evidence_results=[
            make_evidence_result(make_evidence()),
            make_evidence_result(make_evidence(source_hash="TEST-SHA256-DIFFERENT")),
        ]
    )
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "EVIDENCE_ID_CONFLICT"


def test_same_id_different_version_fails() -> None:
    result = assemble(
        evidence_results=[
            make_evidence_result(make_evidence()),
            make_evidence_result(make_evidence(ontology_version="0.0.1-test")),
        ]
    )
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "EVIDENCE_ID_CONFLICT"


def test_empty_evidence_results_fails() -> None:
    result = assemble(evidence_results=[])
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "GOVERNANCE_EVIDENCE_REQUIRED"


def test_fail_evidence_result_fails() -> None:
    result = assemble(evidence_results=[make_source_result(ResultStatus.FAIL)])
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "EVIDENCE_RESULT_NOT_SUCCESSFUL"


def test_warning_evidence_result_fails() -> None:
    result = assemble(evidence_results=[make_source_result(ResultStatus.WARNING)])
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "EVIDENCE_RESULT_NOT_SUCCESSFUL"


def test_pass_without_evidence_fails() -> None:
    result = assemble(evidence_results=[make_evidence_result()])
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "EVIDENCE_RESULT_NOT_SUCCESSFUL"


def test_multiple_successful_results_are_merged() -> None:
    result = assemble(
        evidence_results=[
            make_evidence_result(make_evidence("evidence:TEST-SOURCE-00A")),
            make_evidence_result(make_evidence("evidence:TEST-SOURCE-00B")),
        ],
        findings=[],
    )
    assert result.status is ResultStatus.PASS
    assert len(result.evidence) == 2


def test_evidence_order_follows_input_order() -> None:
    ids = ["evidence:TEST-SOURCE-00A", "evidence:TEST-SOURCE-00B", "evidence:TEST-SOURCE-00C"]
    result = assemble(
        evidence_results=[make_evidence_result(make_evidence(eid)) for eid in ids]
    )
    assert [item.evidence_id for item in result.evidence] == ids


def test_same_input_produces_identical_dump() -> None:
    first = assemble().model_dump(by_alias=True)
    second = assemble().model_dump(by_alias=True)
    assert first == second


# --- C. GovernanceResult 불변조건 전달 (지시 Test 21~27) ---


def test_approved_with_human_review_fails_assembly() -> None:
    result = assemble(human_review_required=True)
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "GOVERNANCE_RESULT_INVALID"


def test_approved_with_error_finding_fails_assembly() -> None:
    result = assemble(findings=[make_finding(FindingSeverity.ERROR)])
    assert result.status is ResultStatus.FAIL


def test_approved_with_fail_source_result_fails_assembly() -> None:
    result = assemble(source_results=[make_source_result(ResultStatus.FAIL)])
    assert result.status is ResultStatus.FAIL


def test_review_required_without_findings_fails_assembly() -> None:
    result = assemble_review(findings=[])
    assert result.status is ResultStatus.FAIL


def test_review_required_without_human_review_fails_assembly() -> None:
    result = assemble_review(human_review_required=False)
    assert result.status is ResultStatus.FAIL


def test_rejected_without_error_finding_fails_assembly() -> None:
    result = assemble_rejected(findings=[make_finding(FindingSeverity.WARNING)])
    assert result.status is ResultStatus.FAIL


def test_dangling_evidence_ref_fails_assembly() -> None:
    result = assemble_review(
        findings=[
            make_finding(
                FindingSeverity.WARNING, evidence_refs=["evidence:TEST-MISSING-SOURCE"]
            )
        ]
    )
    assert result.status is ResultStatus.FAIL


# --- D. Runtime Boundary (지시 Test 28~36) ---


def test_findings_not_list_fails() -> None:
    result = assemble(findings="TEST-MARKER-NOT-LIST")
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "FINDINGS_NOT_LIST"


def test_source_results_not_list_fails() -> None:
    result = assemble(source_results=42)
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "SOURCE_RESULTS_NOT_LIST"


def test_evidence_results_not_list_fails() -> None:
    result = assemble(evidence_results=None)
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "EVIDENCE_RESULTS_NOT_LIST"


def test_invalid_finding_item_fails() -> None:
    result = assemble(findings=["TEST-MARKER-ITEM"])
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "INVALID_FINDING_ITEM"


def test_invalid_source_result_item_fails() -> None:
    result = assemble(source_results=[42])
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "INVALID_SOURCE_RESULT_ITEM"


def test_invalid_evidence_result_item_fails() -> None:
    result = assemble(evidence_results=[make_evidence()])
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "INVALID_EVIDENCE_RESULT_ITEM"


def test_invalid_runtime_inputs_do_not_raise() -> None:
    bad_inputs: list[dict[str, Any]] = [
        {"findings": "TEST-MARKER-NOT-LIST"},
        {"findings": [object()]},
        {"source_results": {"key": "TEST-MARKER-DICT"}},
        {"source_results": [None]},
        {"evidence_results": 42},
        {"evidence_results": ["TEST-MARKER-ITEM"]},
    ]
    for overrides in bad_inputs:
        result = assemble(**overrides)
        assert isinstance(result, SkillResult)
        assert result.status is ResultStatus.FAIL
        assert result.human_review_required is True
        assert len(result.errors) >= 1
        assert result.evidence == []


def test_invalid_input_marker_not_exposed() -> None:
    for overrides in (
        {"findings": "TEST-MARKER-NOT-LIST"},
        {"findings": ["TEST-MARKER-ITEM"]},
        {"source_results": {"key": "TEST-MARKER-DICT"}},
    ):
        dumped = assemble(**overrides).model_dump_json(by_alias=True)
        assert "TEST-MARKER" not in dumped
        assert "builtins." not in dumped


def test_fail_finding_actual_value_is_none() -> None:
    fail_results = [
        assemble(findings="TEST-MARKER-NOT-LIST"),
        assemble(evidence_results=[]),
        assemble(human_review_required=True),
    ]
    for result in fail_results:
        for finding in result.errors:
            assert finding.actual_value is None


# --- E. 직렬화와 실행 Contract (지시 Test 37~41) ---


def test_returns_skill_result_instance() -> None:
    assert isinstance(assemble(), SkillResult)


def test_serialization_contains_camel_case_alias() -> None:
    dumped = assemble().model_dump(by_alias=True)
    assert "humanReviewRequired" in dumped
    assert "human_review_required" not in dumped


def test_success_data_assembled_true() -> None:
    assert assemble().data["assembled"] is True


def test_failure_data_assembled_false() -> None:
    assert assemble(evidence_results=[]).data["assembled"] is False


def test_rejected_assembly_separates_execution_and_decision() -> None:
    result = assemble_rejected()
    assert result.status is ResultStatus.PASS
    assert result.human_review_required is False
    inner = result.data["governanceResult"]
    assert inner["status"] == "REJECTED"
    assert inner["humanReviewRequired"] is True
