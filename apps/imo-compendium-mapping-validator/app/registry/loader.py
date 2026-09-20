"""Registry 적재 (요구사항 3, 4, 5, 7).

- 원본 파일 SHA-256을 snapshot과 audit에 저장한다.
- dry-run은 검증·해시·요약만 수행하고 어떤 Registry 행도 쓰지 않는다.
- 적재는 단일 트랜잭션이다. 어떤 오류에서도 부분 commit이 남지 않는다.
- 기존 버전 행은 삭제·수정하지 않는다 (immutable snapshot).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.registry.models import (
    AuditEvent,
    CompendiumVersion,
    DataElement,
    RefModelOccurrence,
)
from app.registry.sources import parse_source
from app.registry.validator import ValidationIssue, validate_records


@dataclass
class ImportResult:
    ok: bool
    committed: bool
    dry_run: bool
    version: str
    source_hash: str
    source_format: str
    element_count: int
    occurrence_count: int
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def issue_codes(self) -> list[str]:
        return sorted({issue.code for issue in self.issues})


def compute_source_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _audit(
    session_factory: sessionmaker[Session],
    event_type: str,
    version: str,
    source_hash: str,
    detail: dict[str, object],
) -> None:
    """감사 이벤트는 적재 트랜잭션과 분리해 기록한다 (거절 이력도 남긴다)."""
    with session_factory() as session:
        session.add(
            AuditEvent(
                event_type=event_type,
                version=version,
                source_hash=source_hash,
                detail=json.dumps(detail, ensure_ascii=False, sort_keys=True),
            )
        )
        session.commit()


def run_import(
    session_factory: sessionmaker[Session],
    file_path: Path,
    version: str,
    *,
    dry_run: bool = False,
) -> ImportResult:
    source_hash = compute_source_hash(file_path)
    parsed = parse_source(file_path)

    issues: list[ValidationIssue] = [
        ValidationIssue(code=issue.code, row=issue.row, message=issue.message)
        for issue in parsed.issues
    ]
    with session_factory() as session:
        validation = validate_records(parsed.records, version, session)
    issues.extend(validation.issues)

    element_count = len(validation.snapshot.elements)
    occurrence_count = len(validation.snapshot.occurrences)
    detail: dict[str, object] = {
        "sourceFormat": parsed.source_format,
        "recordCount": len(parsed.records),
        "elementCount": element_count,
        "occurrenceCount": occurrence_count,
        "issueCodes": sorted({issue.code for issue in issues}),
        "unknownColumns": parsed.unknown_columns,
        "dryRun": dry_run,
    }

    if dry_run:
        _audit(session_factory, "DRY_RUN", version, source_hash, detail)
        return ImportResult(
            ok=not issues,
            committed=False,
            dry_run=True,
            version=version,
            source_hash=source_hash,
            source_format=parsed.source_format,
            element_count=element_count,
            occurrence_count=occurrence_count,
            issues=issues,
        )

    if issues:
        _audit(session_factory, "IMPORT_REJECTED", version, source_hash, detail)
        return ImportResult(
            ok=False,
            committed=False,
            dry_run=False,
            version=version,
            source_hash=source_hash,
            source_format=parsed.source_format,
            element_count=0,
            occurrence_count=0,
            issues=issues,
        )

    # --- 단일 트랜잭션 적재 (부분 commit 금지) ---
    try:
        with session_factory() as session, session.begin():
            session.add(
                CompendiumVersion(
                    version=version,
                    source_hash=source_hash,
                    source_format=parsed.source_format,
                    element_count=element_count,
                    occurrence_count=occurrence_count,
                    loaded=True,
                )
            )
            for number in sorted(validation.snapshot.elements):
                core = validation.snapshot.elements[number]
                session.add(
                    DataElement(
                        version=version,
                        imo_data_number=number,
                        name=str(core["name"]),
                        definition=core["definition"],
                        format_spec=core["format_spec"],
                        code_list=core["code_list"],
                        business_rule=core["business_rule"],
                        status=str(core["status"]),
                    )
                )
            for number, dataset_key, refmodel_path in validation.snapshot.occurrences:
                session.add(
                    RefModelOccurrence(
                        version=version,
                        imo_data_number=number,
                        dataset_key=dataset_key,
                        refmodel_path=refmodel_path,
                    )
                )
    except SQLAlchemyError:
        failure = ValidationIssue(
            code="IMPORT_TRANSACTION_FAILED",
            row=0,
            message="적재 트랜잭션이 실패하여 전체를 롤백했다",
        )
        detail["issueCodes"] = sorted(
            set(detail["issueCodes"]) | {failure.code}  # type: ignore[arg-type]
        )
        _audit(session_factory, "IMPORT_REJECTED", version, source_hash, detail)
        return ImportResult(
            ok=False,
            committed=False,
            dry_run=False,
            version=version,
            source_hash=source_hash,
            source_format=parsed.source_format,
            element_count=0,
            occurrence_count=0,
            issues=[failure],
        )

    _audit(session_factory, "IMPORT_COMMITTED", version, source_hash, detail)
    return ImportResult(
        ok=True,
        committed=True,
        dry_run=False,
        version=version,
        source_hash=source_hash,
        source_format=parsed.source_format,
        element_count=element_count,
        occurrence_count=occurrence_count,
        issues=[],
    )
