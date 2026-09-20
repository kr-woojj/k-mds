"""적재 전 결정론 검증 (요구사항 1, 2, 4).

- IMO Data Number Pattern `^IMO[0-9]{4}$`만 허용한다.
- 동일 버전 내 중복 IMO Code(핵심 필드 충돌)와 Occurrence 중복을 검사한다.
- 버전 충돌 검사: (a) 대상 버전이 이미 적재됨, (b) 파일에 선언된 version
  컬럼이 CLI 지정 버전과 불일치.
- 검증은 판정만 하고 DB에 쓰지 않는다 (dry-run의 기반).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.registry.models import CompendiumVersion
from app.registry.sources import RegistryRecordInput

IMO_DATA_NUMBER_PATTERN = re.compile(r"^IMO[0-9]{4}$")
ALLOWED_STATUSES = {"active", "added", "changed", "deprecated", "superseded"}

#: 동일 IMO Data Number의 모든 행이 일치해야 하는 핵심 필드
CORE_FIELDS = ("name", "definition", "format_spec", "code_list", "business_rule", "status")


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    row: int
    message: str
    imo_data_number: str | None = None


@dataclass
class NormalizedSnapshot:
    """검증을 통과한 경우에만 채워지는 적재용 정규 구조."""

    elements: dict[str, dict[str, str | None]] = field(default_factory=dict)
    occurrences: list[tuple[str, str | None, str | None]] = field(default_factory=list)


@dataclass
class ValidationResult:
    issues: list[ValidationIssue]
    snapshot: NormalizedSnapshot

    @property
    def ok(self) -> bool:
        return not self.issues


def _version_issues(version: str, session: Session) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not version or len(version) > 64 or version != version.strip():
        issues.append(
            ValidationIssue("VERSION_IDENTIFIER_INVALID", 0, "버전 식별자가 유효하지 않다")
        )
        return issues
    existing = session.execute(
        select(CompendiumVersion.version).where(CompendiumVersion.version == version)
    ).first()
    if existing is not None:
        issues.append(
            ValidationIssue(
                "VERSION_ALREADY_LOADED",
                0,
                "이미 적재된 버전이다 — snapshot은 immutable이며 재적재할 수 없다",
            )
        )
    return issues


def validate_records(
    records: list[RegistryRecordInput], version: str, session: Session
) -> ValidationResult:
    issues: list[ValidationIssue] = list(_version_issues(version, session))
    snapshot = NormalizedSnapshot()

    if not records:
        issues.append(ValidationIssue("EMPTY_SOURCE", 0, "적재할 레코드가 없다"))
        return ValidationResult(issues, snapshot)

    seen_occurrences: set[tuple[str, str | None, str | None]] = set()
    for record in records:
        row = record.source_row
        number = (record.imo_data_number or "").strip().upper()

        if not number or not record.name:
            issues.append(
                ValidationIssue(
                    "MISSING_REQUIRED_FIELD",
                    row,
                    "imo_data_number와 name은 필수다",
                    number or None,
                )
            )
            continue
        if not IMO_DATA_NUMBER_PATTERN.match(number):
            issues.append(
                ValidationIssue(
                    "IMO_NUMBER_PATTERN_INVALID",
                    row,
                    "IMO Data Number는 ^IMO[0-9]{4}$ 패턴만 허용된다",
                    number,
                )
            )
            continue

        status = record.status.strip().lower()
        if status not in ALLOWED_STATUSES:
            issues.append(
                ValidationIssue("INVALID_STATUS", row, "허용되지 않은 status 값이다", number)
            )
            continue

        if record.declared_version is not None and record.declared_version != version:
            issues.append(
                ValidationIssue(
                    "VERSION_FIELD_MISMATCH",
                    row,
                    "파일에 선언된 version이 적재 대상 버전과 다르다",
                    number,
                )
            )
            continue

        core = {
            "name": record.name,
            "definition": record.definition,
            "format_spec": record.format_spec,
            "code_list": record.code_list,
            "business_rule": record.business_rule,
            "status": status,
        }
        existing_core = snapshot.elements.get(number)
        if existing_core is None:
            snapshot.elements[number] = core
        elif existing_core != core:
            issues.append(
                ValidationIssue(
                    "DUPLICATE_IMO_CONFLICT",
                    row,
                    "동일 IMO Data Number의 핵심 필드가 서로 다르다",
                    number,
                )
            )
            continue

        occurrence = (number, record.dataset_key, record.refmodel_path)
        if occurrence in seen_occurrences:
            issues.append(
                ValidationIssue(
                    "DUPLICATE_OCCURRENCE",
                    row,
                    "동일 (IMO, dataset, path) Occurrence가 중복된다",
                    number,
                )
            )
            continue
        seen_occurrences.add(occurrence)
        snapshot.occurrences.append(occurrence)

    if issues:
        # 부분 결과를 반환하지 않는다 (fail-closed).
        return ValidationResult(issues, NormalizedSnapshot())
    snapshot.occurrences.sort(key=lambda item: (item[0], item[1] or "", item[2] or ""))
    return ValidationResult(issues, snapshot)
