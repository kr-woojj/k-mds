"""Registry 적재 모듈 테스트.

정책 (REQ-028): 샘플 IMO 값은 tests/fixtures/ 파일에서만 읽는다.
이 테스트 코드와 app/ 소스에는 IMO Data Number 리터럴을 하드코딩하지 않으며,
기대값은 전부 fixture에서 유도한다.
"""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

import pytest
from sqlalchemy import select

from app.registry.database import init_db, make_session_factory
from app.registry.diff import DiffError, diff_versions
from app.registry.loader import run_import
from app.registry.models import (
    AuditEvent,
    CompendiumVersion,
    DataElement,
    RefModelOccurrence,
)
from app.registry.__main__ import main as cli_main

FIXTURES = Path(__file__).parent / "fixtures"
PROJECT_ROOT = Path(__file__).resolve().parents[1]

NUMBER_COLUMN = "IMO Data Number"
VERSION_COLUMN = "Version"

COMPARABLE_COLUMNS = (
    "Data Element",
    "Definition",
    "Format",
    "Code List",
    "Business Rule",
    "Status",
)


def read_rows(name: str) -> list[dict[str, str]]:
    with (FIXTURES / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def unique_numbers(rows: list[dict[str, str]]) -> set[str]:
    return {row[NUMBER_COLUMN] for row in rows}


def fixture_version(rows: list[dict[str, str]]) -> str:
    return rows[0][VERSION_COLUMN]


@pytest.fixture()
def session_factory(tmp_path: Path):
    engine = init_db(tmp_path / "registry.sqlite3")
    return make_session_factory(engine)


def import_fixture(session_factory, name: str, *, version: str | None = None, dry_run: bool = False):
    rows = read_rows(name)
    target_version = version if version is not None else fixture_version(rows)
    return run_import(
        session_factory, FIXTURES / name, target_version, dry_run=dry_run
    ), rows


# --- 성공 경로 (형식 3종) ---


def test_import_csv_success(session_factory) -> None:
    result, rows = import_fixture(session_factory, "registry_v1.csv")
    assert result.ok is True and result.committed is True
    assert result.element_count == len(unique_numbers(rows))
    assert result.occurrence_count == len(rows)

    with session_factory() as session:
        stored = session.execute(
            select(DataElement.imo_data_number).where(
                DataElement.version == fixture_version(rows)
            )
        ).scalars().all()
        occurrences = session.execute(
            select(RefModelOccurrence).where(
                RefModelOccurrence.version == fixture_version(rows)
            )
        ).scalars().all()
    assert sorted(stored) == sorted(unique_numbers(rows))
    assert len(occurrences) == len(rows)


def test_import_json_success(session_factory) -> None:
    csv_rows = read_rows("registry_v1.csv")
    result = run_import(
        session_factory, FIXTURES / "registry_v1.json", fixture_version(csv_rows)
    )
    assert result.ok is True
    assert result.element_count == len(unique_numbers(csv_rows))
    assert result.occurrence_count == len(csv_rows)


def test_import_xlsx_success(session_factory, tmp_path: Path) -> None:
    import openpyxl

    rows = read_rows("registry_v1.csv")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    headers = list(rows[0].keys())
    sheet.append(headers)
    for row in rows:
        sheet.append([row[column] for column in headers])
    xlsx_path = tmp_path / "registry_v1.xlsx"
    workbook.save(xlsx_path)

    result = run_import(session_factory, xlsx_path, fixture_version(rows))
    assert result.ok is True
    assert result.element_count == len(unique_numbers(rows))
    assert result.occurrence_count == len(rows)


# --- 요구사항 3: 원본 hash 저장 ---


def test_source_hash_stored(session_factory) -> None:
    result, rows = import_fixture(session_factory, "registry_v1.csv")
    expected = hashlib.sha256((FIXTURES / "registry_v1.csv").read_bytes()).hexdigest()
    assert result.source_hash == expected
    with session_factory() as session:
        version_row = session.get(CompendiumVersion, fixture_version(rows))
    assert version_row is not None
    assert version_row.source_hash == expected
    assert version_row.loaded is True


# --- 요구사항 2: 패턴 강제 + 요구사항 7: 부분 commit 금지 ---


def test_invalid_pattern_rejected_without_partial_commit(session_factory) -> None:
    result, rows = import_fixture(session_factory, "registry_invalid_pattern.csv")
    assert result.ok is False and result.committed is False
    assert "IMO_NUMBER_PATTERN_INVALID" in result.issue_codes
    with session_factory() as session:
        versions = session.execute(select(CompendiumVersion)).scalars().all()
        elements = session.execute(select(DataElement)).scalars().all()
    # 유효한 행이 섞여 있어도 어떤 행도 commit되지 않아야 한다.
    assert versions == [] and elements == []


# --- 요구사항 1: 중복 IMO Code ---


def test_duplicate_conflict_rejected(session_factory) -> None:
    result, _ = import_fixture(session_factory, "registry_conflict.csv")
    assert result.ok is False and result.committed is False
    assert "DUPLICATE_IMO_CONFLICT" in result.issue_codes


def test_same_number_multiple_paths_is_not_conflict(session_factory) -> None:
    # 핵심 필드가 동일하면 다중 Reference Model Path는 Occurrence로 병합된다.
    result, rows = import_fixture(session_factory, "registry_v1.csv")
    assert result.ok is True
    assert result.occurrence_count > result.element_count


# --- 요구사항 1·5: 버전 충돌과 immutable snapshot ---


def test_version_already_loaded_rejected(session_factory) -> None:
    first, rows = import_fixture(session_factory, "registry_v1.csv")
    assert first.ok is True
    second, _ = import_fixture(session_factory, "registry_v1.csv")
    assert second.ok is False
    assert "VERSION_ALREADY_LOADED" in second.issue_codes
    with session_factory() as session:
        count = len(
            session.execute(
                select(DataElement).where(
                    DataElement.version == fixture_version(rows)
                )
            ).scalars().all()
        )
    assert count == len(unique_numbers(rows))


def test_version_field_mismatch_rejected(session_factory) -> None:
    rows = read_rows("registry_v1.csv")
    mismatched = fixture_version(rows) + "-OTHER"
    result = run_import(session_factory, FIXTURES / "registry_v1.csv", mismatched)
    assert result.ok is False
    assert "VERSION_FIELD_MISMATCH" in result.issue_codes


def test_previous_snapshot_unchanged_after_new_version(session_factory) -> None:
    first, v1_rows = import_fixture(session_factory, "registry_v1.csv")
    v1 = fixture_version(v1_rows)
    with session_factory() as session:
        before = {
            (e.imo_data_number, e.name, e.definition, e.format_spec, e.status)
            for e in session.execute(
                select(DataElement).where(DataElement.version == v1)
            ).scalars()
        }
    second, _ = import_fixture(session_factory, "registry_v2.csv")
    assert second.ok is True
    with session_factory() as session:
        after = {
            (e.imo_data_number, e.name, e.definition, e.format_spec, e.status)
            for e in session.execute(
                select(DataElement).where(DataElement.version == v1)
            ).scalars()
        }
        version_rows = session.execute(select(CompendiumVersion)).scalars().all()
    assert before == after
    assert len(version_rows) == 2


# --- 요구사항 4: dry-run ---


def test_dry_run_validates_without_writing(session_factory) -> None:
    result, rows = import_fixture(session_factory, "registry_v1.csv", dry_run=True)
    assert result.ok is True and result.committed is False and result.dry_run is True
    assert result.element_count == len(unique_numbers(rows))
    with session_factory() as session:
        versions = session.execute(select(CompendiumVersion)).scalars().all()
        events = session.execute(select(AuditEvent)).scalars().all()
    assert versions == []
    assert [event.event_type for event in events] == ["DRY_RUN"]


# --- 요구사항 6: diff ---


def _expected_diff(v1_rows, v2_rows):
    v1_numbers = unique_numbers(v1_rows)
    v2_numbers = unique_numbers(v2_rows)
    added = sorted(v2_numbers - v1_numbers)
    removed = sorted(v1_numbers - v2_numbers)

    def core(rows, number):
        for row in rows:
            if row[NUMBER_COLUMN] == number:
                return tuple(row[column] for column in COMPARABLE_COLUMNS)
        return None

    modified = sorted(
        number
        for number in v1_numbers & v2_numbers
        if core(v1_rows, number) != core(v2_rows, number)
    )
    return added, modified, removed


def test_diff_added_modified_deprecated(session_factory) -> None:
    _, v1_rows = import_fixture(session_factory, "registry_v1.csv")
    _, v2_rows = import_fixture(session_factory, "registry_v2.csv")
    expected_added, expected_modified, expected_removed = _expected_diff(
        v1_rows, v2_rows
    )

    diff = diff_versions(
        session_factory, fixture_version(v1_rows), fixture_version(v2_rows)
    )
    assert diff.added == expected_added
    assert diff.deprecated == expected_removed
    assert [item["imoDataNumber"] for item in diff.modified] == expected_modified
    for item in diff.modified:
        assert item["changedFields"]


def test_diff_status_transition_counts_as_deprecated(session_factory) -> None:
    _, v1_rows = import_fixture(session_factory, "registry_v1.csv")
    _, v3_rows = import_fixture(session_factory, "registry_v3.csv")
    # v3에서 status가 deprecated로 전환된 번호를 fixture에서 유도한다.
    transitioned = sorted(
        row[NUMBER_COLUMN]
        for row in v3_rows
        if row["Status"].strip().lower() == "deprecated"
    )
    diff = diff_versions(
        session_factory, fixture_version(v1_rows), fixture_version(v3_rows)
    )
    for number in transitioned:
        assert number in diff.deprecated
        assert number not in [item["imoDataNumber"] for item in diff.modified]


def test_diff_unknown_version_fails(session_factory) -> None:
    _, v1_rows = import_fixture(session_factory, "registry_v1.csv")
    with pytest.raises(DiffError):
        diff_versions(
            session_factory, fixture_version(v1_rows), fixture_version(v1_rows) + "-X"
        )


# --- CLI ---


def test_cli_import_and_diff(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db_path = tmp_path / "cli.sqlite3"
    v1_rows = read_rows("registry_v1.csv")
    v2_rows = read_rows("registry_v2.csv")

    exit_code = cli_main(
        [
            "import",
            "--file",
            str(FIXTURES / "registry_v1.csv"),
            "--version",
            fixture_version(v1_rows),
            "--db",
            str(db_path),
        ]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "ok=true" in out and "committed=true" in out

    assert (
        cli_main(
            [
                "import",
                "--file",
                str(FIXTURES / "registry_v2.csv"),
                "--version",
                fixture_version(v2_rows),
                "--db",
                str(db_path),
            ]
        )
        == 0
    )
    capsys.readouterr()

    exit_code = cli_main(
        [
            "diff",
            "--from",
            fixture_version(v1_rows),
            "--to",
            fixture_version(v2_rows),
            "--db",
            str(db_path),
        ]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    expected_added, expected_modified, expected_removed = _expected_diff(
        v1_rows, v2_rows
    )
    assert f"addedCount={len(expected_added)}" in out
    assert f"modifiedCount={len(expected_modified)}" in out
    assert f"deprecatedCount={len(expected_removed)}" in out


def test_cli_import_failure_exit_code(tmp_path: Path, capsys) -> None:
    rows = read_rows("registry_invalid_pattern.csv")
    exit_code = cli_main(
        [
            "import",
            "--file",
            str(FIXTURES / "registry_invalid_pattern.csv"),
            "--version",
            fixture_version(rows),
            "--db",
            str(tmp_path / "cli.sqlite3"),
        ]
    )
    assert exit_code == 1
    assert "ok=false" in capsys.readouterr().out


# --- 정책: 소스 코드에 IMO 리터럴 금지 (REQ-028, threat-model T-08) ---


def test_no_hardcoded_imo_values_in_app_source() -> None:
    literal = re.compile(r"IMO\d{4}")
    offenders: list[str] = []
    for source in (PROJECT_ROOT / "app").rglob("*.py"):
        if literal.search(source.read_text(encoding="utf-8")):
            offenders.append(source.name)
    assert offenders == []
