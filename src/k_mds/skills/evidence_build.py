"""evidence_build Skill (ADR-0003).

검증된 SourceManifestEntry에서만 Evidence를 결정론적으로 생성하고 항상
SkillResult를 반환한다. Hash를 계산하거나 추측하지 않으며 random·uuid·
timestamp를 사용하지 않는다. Finding에는 원본 입력값, source_hash,
source_file 경로를 포함하지 않는다.
"""

from __future__ import annotations

from pydantic import ValidationError

from k_mds.models import (
    Evidence,
    FindingSeverity,
    GovernanceStatus,
    ResultStatus,
    SkillResult,
    SourceManifestEntry,
    ValidationFinding,
)

RULE_ID = "urn:k-mds:rule:evidence-provenance:0.1"


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
        data={"verified": False},
        errors=errors,
    )


def _loc_to_path(loc: tuple[int | str, ...]) -> str:
    if not loc:
        return "$"
    return "$." + ".".join(str(part) for part in loc)


def evidence_build(entry: SourceManifestEntry | dict[str, object]) -> SkillResult:
    """검증된 Source Manifest Entry에서 Evidence를 생성한다.

    evidence_id는 "evidence:" + source_id로 결정론적으로 구성한다.
    """
    if isinstance(entry, dict):
        try:
            validated = SourceManifestEntry.model_validate(entry)
        except ValidationError as exc:
            errors = [
                _finding(
                    "SOURCE_ENTRY_INVALID",
                    str(item["msg"]),
                    path=_loc_to_path(item["loc"]),
                )
                for item in exc.errors(
                    include_url=False, include_input=False, include_context=False
                )
            ]
            return _fail(errors)
    else:
        validated = entry

    if not validated.verified:
        return _fail(
            [
                _finding(
                    "SOURCE_NOT_VERIFIED",
                    "검증되지 않은 Source Entry로는 Evidence를 생성할 수 없다",
                    path="$.verified",
                )
            ]
        )

    if validated.status is not GovernanceStatus.APPROVED:
        return _fail(
            [
                _finding(
                    "SOURCE_NOT_APPROVED",
                    f"approved 상태의 Source Entry만 허용된다 (현재: {validated.status.value})",
                    path="$.status",
                )
            ]
        )

    evidence = Evidence(
        evidence_id=f"evidence:{validated.source_id}",
        fal_version=validated.fal_version,
        ontology_version=validated.ontology_version,
        profile_version=validated.profile_version,
        source_file=validated.source_file,
        source_hash=validated.source_hash,
        resource_uri=validated.resource_uri,
    )
    return SkillResult(
        status=ResultStatus.PASS,
        human_review_required=False,
        data={
            "sourceId": validated.source_id,
            "evidenceId": evidence.evidence_id,
            "verified": True,
        },
        evidence=[evidence],
    )
