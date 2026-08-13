"""governance_assemble Skill — Final Governance Result Assembler (ADR-0005).

명시적으로 제공된 Governance Decision 정보, Low-level SkillResult,
evidence_build 결과를 결합해 GovernanceResult를 조립한다.

핵심 원칙:
- Governance 상태를 source_results에서 추론하지 않는다 — 호출자가 명시한다.
- Assembler 실행 성공과 Governance Decision 결과를 구분한다.
  REJECTED 결정을 정상 조립해도 바깥 SkillResult는 PASS다.
- 공식 Evidence는 evidence_build 결과(evidence_results)에서만 수집하며
  source_results 내부 Evidence는 자동 승격하지 않는다.
- 예외를 외부로 던지지 않고 입력·조립 실패는 SkillResult.FAIL로 반환한다.
"""

from __future__ import annotations

from pydantic import ValidationError

from k_mds.models import (
    Evidence,
    FindingSeverity,
    GovernanceDecisionStatus,
    GovernanceDecisionType,
    GovernanceResult,
    ResultStatus,
    SkillResult,
    ValidationFinding,
)

RULE_ID = "urn:k-mds:rule:governance-assembly:0.1"


def _finding(code: str, message: str, path: str | None = None) -> ValidationFinding:
    return ValidationFinding(
        severity=FindingSeverity.ERROR,
        code=code,
        message=message,
        rule_id=RULE_ID,
        path=path,
        actual_value=None,
    )


def _fail(errors: list[ValidationFinding]) -> SkillResult:
    return SkillResult(
        status=ResultStatus.FAIL,
        human_review_required=True,
        data={"assembled": False},
        errors=errors,
    )


def _loc_to_path(loc: tuple[int | str, ...]) -> str:
    if not loc:
        return "$"
    return "$." + ".".join(str(part) for part in loc)


def _check_list_boundary(
    findings: object, source_results: object, evidence_results: object
) -> list[ValidationFinding]:
    """list 및 항목 타입 경계를 검사한다. 입력값·repr·타입 경로는 노출하지 않는다."""
    errors: list[ValidationFinding] = []
    boundaries: list[tuple[str, object, type, str, str, str]] = [
        ("findings", findings, ValidationFinding, "FINDINGS_NOT_LIST",
         "INVALID_FINDING_ITEM", "ValidationFinding"),
        ("sourceResults", source_results, SkillResult, "SOURCE_RESULTS_NOT_LIST",
         "INVALID_SOURCE_RESULT_ITEM", "SkillResult"),
        ("evidenceResults", evidence_results, SkillResult, "EVIDENCE_RESULTS_NOT_LIST",
         "INVALID_EVIDENCE_RESULT_ITEM", "SkillResult"),
    ]
    for name, value, item_type, list_code, item_code, type_name in boundaries:
        if not isinstance(value, list):
            errors.append(_finding(list_code, f"{name}은(는) list여야 한다", path=f"$.{name}"))
            continue
        for index, item in enumerate(value):
            if not isinstance(item, item_type):
                errors.append(
                    _finding(
                        item_code,
                        f"{name}[{index}] 항목은 {type_name}이어야 한다",
                        path=f"$.{name}.{index}",
                    )
                )
    return errors


def _collect_evidence(
    evidence_results: list[SkillResult],
) -> tuple[list[Evidence], list[ValidationFinding]]:
    """evidence_build 결과에서만 Evidence를 수집·병합한다. 입력 순서를 유지한다."""
    collected: list[Evidence] = []
    by_id: dict[str, Evidence] = {}
    errors: list[ValidationFinding] = []

    for index, result in enumerate(evidence_results):
        if result.status is not ResultStatus.PASS or result.errors or not result.evidence:
            errors.append(
                _finding(
                    "EVIDENCE_RESULT_NOT_SUCCESSFUL",
                    f"evidenceResults[{index}]은(는) 성공한 Evidence 결과가 아니다 "
                    "(PASS 상태, 오류 없음, Evidence 1개 이상 필요)",
                    path=f"$.evidenceResults.{index}",
                )
            )
            continue
        for item in result.evidence:
            existing = by_id.get(item.evidence_id)
            if existing is None:
                by_id[item.evidence_id] = item
                collected.append(item)
            elif existing != item:
                errors.append(
                    _finding(
                        "EVIDENCE_ID_CONFLICT",
                        "동일 evidence_id에 서로 다른 내용의 Evidence가 존재한다: "
                        f"{item.evidence_id}",
                        path=f"$.evidenceResults.{index}",
                    )
                )
            # 동일 evidence_id·동일 내용은 deduplicate한다.
    return collected, errors


def governance_assemble(
    *,
    decision_id: str,
    decision_type: GovernanceDecisionType | str,
    status: GovernanceDecisionStatus | str,
    subject_id: str,
    summary: str,
    rationale: str,
    findings: list[ValidationFinding],
    source_results: list[SkillResult],
    evidence_results: list[SkillResult],
    human_review_required: bool,
) -> SkillResult:
    """검증된 Evidence 결과와 명시된 Decision 정보로 GovernanceResult를 조립한다."""
    boundary_errors = _check_list_boundary(findings, source_results, evidence_results)
    if boundary_errors:
        return _fail(boundary_errors)

    collected, evidence_errors = _collect_evidence(evidence_results)
    if evidence_errors:
        return _fail(evidence_errors)
    if not collected:
        return _fail(
            [
                _finding(
                    "GOVERNANCE_EVIDENCE_REQUIRED",
                    "Governance Decision에는 검증된 Evidence가 최소 1개 필요하다",
                    path="$.evidenceResults",
                )
            ]
        )

    try:
        governance = GovernanceResult.model_validate(
            {
                "decision_id": decision_id,
                "decision_type": decision_type,
                "status": status,
                "subject_id": subject_id,
                "summary": summary,
                "rationale": rationale,
                "evidence": collected,
                "findings": findings,
                "source_results": source_results,
                "human_review_required": human_review_required,
            }
        )
    except ValidationError as exc:
        errors = [
            _finding(
                "GOVERNANCE_RESULT_INVALID",
                str(item["msg"]),
                path=_loc_to_path(item["loc"]),
            )
            for item in exc.errors(
                include_url=False, include_input=False, include_context=False
            )
        ]
        return _fail(errors)

    return SkillResult(
        status=ResultStatus.PASS,
        human_review_required=False,
        data={
            "assembled": True,
            "governanceStatus": governance.status.value,
            "decisionId": governance.decision_id,
            "governanceResult": governance.model_dump(by_alias=True, mode="json"),
        },
        evidence=list(governance.evidence),
    )
