"""normalize_compendium Contract Test (ADR-0009).

실제 FAL50 원본, Local Restricted Manifest, 실제 Inspection Report에는
절대 접근하지 않는다. 모든 입력은 tmp_path의 Synthetic Fixture이며
TEST/FALTEST/urn:test 표기만 사용한다.
"""

import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import openpyxl  # type: ignore[import-untyped]
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import inspect_excel  # noqa: E402
import normalize_compendium  # noqa: E402

WORKBOOK_NAME = "TEST-MARKER-WORKBOOK.xlsx"

DEFAULT_ROWS: list[list[Any]] = [
    ["TEST-HEADER-A", "TEST-HEADER-B", "TEST-HEADER-C"],
    ["TEST-ID-001", "TEST-NAME-001", 10],
    ["TEST-ID-002", "TEST-NAME-002", 20],
]

ARTIFACT_NAMES = (
    "normalized-records.local.json",
    "normalization-findings.local.json",
    "mapping-evidence.local.json",
    "normalization-summary.local.json",
)


def sha256_of_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def default_spec(**overrides: Any) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "version": 1,
        "dataset_id": "TEST-DATASET-001",
        "source_sheet_ordinal": 0,
        "header_row": 1,
        "first_data_row": 2,
        "columns": [
            {
                "source_column_ordinal": 1,
                "target_field": "test_identifier",
                "required": True,
                "value_type": "string",
            },
            {
                "source_column_ordinal": 2,
                "target_field": "test_name",
                "required": True,
                "value_type": "string",
            },
            {
                "source_column_ordinal": 3,
                "target_field": "test_number",
                "required": False,
                "value_type": "number",
            },
        ],
    }
    spec.update(overrides)
    return spec


def make_env(
    tmp_path: Path,
    rows: list[list[Any]] | None = None,
    spec: dict[str, Any] | None = None,
) -> dict[str, Path]:
    base = tmp_path / "sourcebase"
    (base / "files").mkdir(parents=True)
    workbook = base / "files" / WORKBOOK_NAME
    wb = openpyxl.Workbook()
    # openpyxl 기본 <workbookProtection/> 요소가 Inspector에서 Protection으로
    # 탐지되어 normalizationReady=false가 되므로 Synthetic Fixture에서 제거한다.
    wb.security = None
    ws = wb.active
    ws.title = "TEST-SHEET-ALPHA"
    for row in rows if rows is not None else DEFAULT_ROWS:
        ws.append(row)
    wb.save(workbook)

    manifest = base / "source-manifest.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "sources": [
                    {
                        "source_id": "TEST-SOURCE-001",
                        "fal_version": "FALTEST",
                        "ontology_version": "0.0.0-test",
                        "profile_version": "kr-profile-0.0.0-test",
                        "source_file": f"files/{WORKBOOK_NAME}",
                        "source_hash": sha256_of_file(workbook),
                        "resource_uri": "urn:test:source:001",
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    report = inspect_excel.inspect_workbook(
        workbook,
        manifest_path=manifest,
        options=inspect_excel.InspectionOptions(
            max_rows_per_sheet=5000, max_columns_per_sheet=200
        ),
    )
    report_path = tmp_path / "inspection-report.local.json"
    report_path.write_text(inspect_excel.serialize_report(report), encoding="utf-8")

    spec_path = tmp_path / "mapping-spec.local.yaml"
    spec_path.write_text(
        yaml.safe_dump(spec if spec is not None else default_spec(), allow_unicode=True),
        encoding="utf-8",
    )

    out = tmp_path / "out"
    out.mkdir()
    return {
        "workbook": workbook,
        "manifest": manifest,
        "base": base,
        "report": report_path,
        "spec": spec_path,
        "out": out,
    }


def mutate_report(env: dict[str, Path], mutate: Any) -> None:
    report = json.loads(env["report"].read_text(encoding="utf-8"))
    mutate(report)
    env["report"].write_text(
        inspect_excel.serialize_report(report), encoding="utf-8"
    )


def run_norm(env: dict[str, Path], **options: Any) -> dict[str, Any]:
    return normalize_compendium.normalize_compendium(
        workbook_path=env["workbook"],
        manifest_path=env["manifest"],
        source_base_dir=env["base"],
        inspection_report_path=env["report"],
        mapping_spec_path=env["spec"],
        output_dir=env["out"],
        options=normalize_compendium.NormalizationOptions(**options),
    )


def finding_codes(result: dict[str, Any]) -> list[str]:
    return [finding["code"] for finding in result["findings"]]


# --- A. Gate ---


def test_verified_synthetic_normalization_succeeds(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    result = run_norm(env)
    assert result["completed"] is True
    assert result["summary"]["normalizedRecordCount"] == 2
    for name in ARTIFACT_NAMES:
        assert (env["out"] / name).is_file()


def test_unverified_provenance_rejected(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    mutate_report(env, lambda r: r.update(provenanceVerified=False))
    result = run_norm(env)
    assert result["completed"] is False
    assert "INSPECTION_NOT_VERIFIED" in finding_codes(result)


def test_pending_manifest_status_rejected(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    mutate_report(env, lambda r: r.update(manifestStatus="pending"))
    assert run_norm(env)["completed"] is False


def test_local_unverified_mode_rejected(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    mutate_report(env, lambda r: r.update(inspectionMode="local-unverified-source"))
    assert run_norm(env)["completed"] is False


def test_incomplete_inspection_rejected(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    mutate_report(env, lambda r: r["summary"].update(inspectionCompleted=False))
    assert run_norm(env)["completed"] is False


def test_not_normalization_ready_rejected(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    mutate_report(env, lambda r: r["summary"].update(normalizationReady=False))
    result = run_norm(env)
    assert result["completed"] is False
    assert "INSPECTION_NOT_NORMALIZATION_READY" in finding_codes(result)


def test_scan_limit_finding_rejected(tmp_path: Path) -> None:
    env = make_env(tmp_path)

    def add_scan_finding(report: dict[str, Any]) -> None:
        report["findings"].append(
            {
                "severity": "WARNING",
                "code": "WORKBOOK_SCAN_LIMIT_REACHED",
                "message": "TEST",
                "path": "$.sheets.0",
                "actualValue": None,
            }
        )

    mutate_report(env, add_scan_finding)
    result = run_norm(env)
    assert result["completed"] is False
    assert "INSPECTION_SCAN_INCOMPLETE" in finding_codes(result)


def test_header_not_detected_sheet_rejected(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    mutate_report(
        env,
        lambda r: r["sheets"][0].update(inferredHeaderRow=None, headerConfidence="none"),
    )
    result = run_norm(env)
    assert result["completed"] is False
    assert "INSPECTION_HEADER_MISMATCH" in finding_codes(result)


def test_sheet_out_of_range_rejected(tmp_path: Path) -> None:
    env = make_env(tmp_path, spec=default_spec(source_sheet_ordinal=7))
    result = run_norm(env)
    assert result["completed"] is False
    assert "INSPECTION_SHEET_OUT_OF_RANGE" in finding_codes(result)


def test_header_row_mismatch_rejected(tmp_path: Path) -> None:
    env = make_env(tmp_path, spec=default_spec(header_row=3, first_data_row=4))
    result = run_norm(env)
    assert result["completed"] is False
    assert "INSPECTION_HEADER_MISMATCH" in finding_codes(result)


def test_source_id_mismatch_rejected(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    mutate_report(env, lambda r: r.update(sourceId="TEST-SOURCE-OTHER"))
    result = run_norm(env)
    assert result["completed"] is False
    assert "SOURCE_ID_MISMATCH" in finding_codes(result)


def test_manifest_hash_mismatch_rejected(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    text = env["manifest"].read_text(encoding="utf-8")
    env["manifest"].write_text(
        text.replace(sha256_of_file(env["workbook"]), "f" * 64), encoding="utf-8"
    )
    result = run_norm(env)
    assert result["completed"] is False
    assert "MANIFEST_VERIFICATION_FAILED" in finding_codes(result)


# --- B. Mapping Spec ---


def test_valid_mapping_spec_accepted(tmp_path: Path) -> None:
    assert run_norm(make_env(tmp_path))["completed"] is True


def test_duplicate_source_column_rejected(tmp_path: Path) -> None:
    spec = default_spec()
    spec["columns"][1]["source_column_ordinal"] = 1
    result = run_norm(make_env(tmp_path, spec=spec))
    assert result["completed"] is False


def test_duplicate_target_field_rejected(tmp_path: Path) -> None:
    spec = default_spec()
    spec["columns"][1]["target_field"] = "test_identifier"
    assert run_norm(make_env(tmp_path, spec=spec))["completed"] is False


def test_empty_columns_rejected(tmp_path: Path) -> None:
    assert run_norm(make_env(tmp_path, spec=default_spec(columns=[])))["completed"] is False


def test_first_data_row_not_after_header_rejected(tmp_path: Path) -> None:
    spec = default_spec(first_data_row=1)
    assert run_norm(make_env(tmp_path, spec=spec))["completed"] is False


def test_extra_spec_field_rejected(tmp_path: Path) -> None:
    spec = default_spec(unexpected_field="TEST")
    assert run_norm(make_env(tmp_path, spec=spec))["completed"] is False


def test_spec_needs_no_header_text_or_sheet_name(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    spec_text = env["spec"].read_text(encoding="utf-8")
    assert "TEST-HEADER" not in spec_text
    assert "TEST-SHEET" not in spec_text
    assert run_norm(env)["completed"] is True


# --- C. Type Normalize ---


def type_env(tmp_path: Path, value: Any, value_type: str, required: bool = False
             ) -> dict[str, Path]:
    rows: list[list[Any]] = [["TEST-HEADER-A", "TEST-HEADER-B"], ["TEST-ID-001", value]]
    spec = default_spec()
    spec["columns"] = [
        {
            "source_column_ordinal": 1,
            "target_field": "test_identifier",
            "required": True,
            "value_type": "string",
        },
        {
            "source_column_ordinal": 2,
            "target_field": "test_value",
            "required": required,
            "value_type": value_type,
        },
    ]
    return make_env(tmp_path, rows=rows, spec=spec)


def first_value(result: dict[str, Any]) -> Any:
    records = result["artifacts"]["normalized-records.local.json"]["records"]
    return records[0]["values"]["test_value"]


def test_string_is_trimmed(tmp_path: Path) -> None:
    result = run_norm(type_env(tmp_path, "  TEST-TRIM  ", "string"))
    assert first_value(result) == "TEST-TRIM"


def test_empty_string_becomes_null(tmp_path: Path) -> None:
    result = run_norm(type_env(tmp_path, "   ", "string"))
    assert first_value(result) is None


def test_number_succeeds(tmp_path: Path) -> None:
    assert first_value(run_norm(type_env(tmp_path, 12.5, "number"))) == 12.5


def test_bool_rejected_as_number(tmp_path: Path) -> None:
    result = run_norm(type_env(tmp_path, True, "number"))
    assert result["summary"]["rejectedRecordCount"] == 1
    assert "VALUE_TYPE_MISMATCH" in finding_codes(result)


def test_integer_succeeds(tmp_path: Path) -> None:
    assert first_value(run_norm(type_env(tmp_path, 10, "integer"))) == 10


def test_decimal_integer_rejected(tmp_path: Path) -> None:
    result = run_norm(type_env(tmp_path, 10.5, "integer"))
    assert result["summary"]["rejectedRecordCount"] == 1


def test_boolean_succeeds(tmp_path: Path) -> None:
    assert first_value(run_norm(type_env(tmp_path, True, "boolean"))) is True


def test_non_bool_boolean_rejected(tmp_path: Path) -> None:
    result = run_norm(type_env(tmp_path, 1, "boolean"))
    assert result["summary"]["rejectedRecordCount"] == 1


def test_date_serialized_iso(tmp_path: Path) -> None:
    result = run_norm(type_env(tmp_path, datetime.date(2020, 1, 2), "date"))
    assert first_value(result) == "2020-01-02"


def test_formula_rejected(tmp_path: Path) -> None:
    env = type_env(tmp_path, "=SUM(1,2)", "number")
    # Formula Workbook은 Inspector가 WORKBOOK_FORMULA_PRESENT를 남기므로
    # Human Review 승인된 Report를 시뮬레이션한다 (Normalizer 자체 방어 검증).
    mutate_report(
        env,
        lambda r: (r.update(findings=[]), r["summary"].update(normalizationReady=True)),
    )
    result = run_norm(env)
    assert result["summary"]["rejectedRecordCount"] == 1
    assert "FORMULA_VALUE_PROHIBITED" in finding_codes(result)


def test_required_missing_rejected(tmp_path: Path) -> None:
    result = run_norm(type_env(tmp_path, None, "string", required=True))
    assert result["summary"]["rejectedRecordCount"] == 1
    assert "REQUIRED_VALUE_MISSING" in finding_codes(result)


# --- D. Row 처리 ---


def test_row_order_and_ordinals(tmp_path: Path) -> None:
    result = run_norm(make_env(tmp_path))
    records = result["artifacts"]["normalized-records.local.json"]["records"]
    assert [record["recordOrdinal"] for record in records] == [0, 1]
    assert [record["sourceRowOrdinal"] for record in records] == [2, 3]
    assert records[0]["values"]["test_identifier"] == "TEST-ID-001"
    assert records[1]["values"]["test_identifier"] == "TEST-ID-002"


def test_blank_row_skipped(tmp_path: Path) -> None:
    rows: list[list[Any]] = [
        ["TEST-HEADER-A", "TEST-HEADER-B", "TEST-HEADER-C"],
        ["TEST-ID-001", "TEST-NAME-001", 10],
        [None, None, None],
        ["TEST-ID-002", "TEST-NAME-002", 20],
    ]
    result = run_norm(make_env(tmp_path, rows=rows))
    summary = result["summary"]
    assert summary["normalizedRecordCount"] == 2
    assert summary["sourceRecordCount"] == 2
    assert summary["rejectedRecordCount"] == 0


def test_rejected_rows_not_in_records(tmp_path: Path) -> None:
    rows: list[list[Any]] = [
        ["TEST-HEADER-A", "TEST-HEADER-B", "TEST-HEADER-C"],
        ["TEST-ID-001", "TEST-NAME-001", 10],
        ["TEST-ID-002", None, 20],
        ["TEST-ID-003", "TEST-NAME-003", "TEST-NOT-A-NUMBER"],
    ]
    result = run_norm(make_env(tmp_path, rows=rows))
    summary = result["summary"]
    assert summary["sourceRecordCount"] == 3
    assert summary["normalizedRecordCount"] == 1
    assert summary["rejectedRecordCount"] == 2
    records = result["artifacts"]["normalized-records.local.json"]["records"]
    identifiers = [record["values"]["test_identifier"] for record in records]
    assert identifiers == ["TEST-ID-001"]


# --- E. Output Security ---


def test_repo_normalized_ignored_output_allowed(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    out = REPO_ROOT / "data" / "normalized" / f"TEST-NORM-{os.getpid()}"
    out.mkdir(parents=True)
    try:
        env["out"] = out
        result = run_norm(env)
        assert result["completed"] is True
        for name in ARTIFACT_NAMES:
            target = out / name
            assert target.is_file()
            rel = target.relative_to(REPO_ROOT).as_posix()
            check = subprocess.run(
                ["git", "check-ignore", rel], capture_output=True, cwd=str(REPO_ROOT)
            )
            assert check.returncode == 0, f"{name} 이(가) ignore되지 않았다"
            tracked = subprocess.run(
                ["git", "ls-files", "--", rel],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            ).stdout.strip()
            assert tracked == ""
        cached = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--", "data/normalized"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        ).stdout.strip()
        assert cached == ""
    finally:
        shutil.rmtree(out, ignore_errors=True)


def _expect_output_rejected(env: dict[str, Path], out: Path, code: str) -> None:
    env["out"] = out
    result = run_norm(env)
    assert result["completed"] is False
    assert code in finding_codes(result)


def test_repo_root_output_rejected(tmp_path: Path) -> None:
    _expect_output_rejected(make_env(tmp_path), REPO_ROOT, "OUTPUT_DIR_NOT_RESTRICTED")


def test_data_raw_output_rejected(tmp_path: Path) -> None:
    _expect_output_rejected(
        make_env(tmp_path), REPO_ROOT / "data" / "raw", "OUTPUT_DIR_NOT_RESTRICTED"
    )


def test_src_output_rejected(tmp_path: Path) -> None:
    _expect_output_rejected(
        make_env(tmp_path), REPO_ROOT / "src", "OUTPUT_DIR_NOT_RESTRICTED"
    )


def test_tests_output_rejected(tmp_path: Path) -> None:
    _expect_output_rejected(
        make_env(tmp_path), REPO_ROOT / "tests", "OUTPUT_DIR_NOT_RESTRICTED"
    )


def test_symlink_escape_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "escape-target"
    outside.mkdir()
    link = REPO_ROOT / "data" / "normalized" / f"TEST-LINK-{os.getpid()}"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("이 환경에서는 Symlink 생성이 지원되지 않는다")
    try:
        _expect_output_rejected(make_env(tmp_path), link, "OUTPUT_DIR_NOT_RESTRICTED")
    finally:
        link.unlink(missing_ok=True)


def test_existing_output_rejected(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    (env["out"] / ARTIFACT_NAMES[0]).write_text("{}\n", encoding="utf-8")
    result = run_norm(env)
    assert result["completed"] is False
    assert "OUTPUT_ALREADY_EXISTS" in finding_codes(result)


def test_partial_write_failure_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = make_env(tmp_path)
    original = normalize_compendium.serialize_artifact
    calls = {"count": 0}

    def _fail_on_third(data: dict[str, object]) -> str:
        calls["count"] += 1
        if calls["count"] >= 3:
            raise ValueError("TEST-SERIALIZE-FAILURE")
        return original(data)

    monkeypatch.setattr(normalize_compendium, "serialize_artifact", _fail_on_third)
    result = run_norm(env)
    assert result["completed"] is False
    assert "OUTPUT_WRITE_FAILED" in finding_codes(result)
    assert list(env["out"].iterdir()) == []


def test_inputs_unchanged(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    before = {
        key: sha256_of_file(env[key]) for key in ("workbook", "manifest", "report", "spec")
    }
    run_norm(env)
    after = {
        key: sha256_of_file(env[key]) for key in ("workbook", "manifest", "report", "spec")
    }
    assert before == after


# --- F. 결정론과 비노출 ---


def test_same_input_same_result_and_bytes(tmp_path: Path) -> None:
    env_a = make_env(tmp_path / "a")
    env_b = make_env(tmp_path / "b")
    result_a = run_norm(env_a)
    result_b = run_norm(env_b)
    assert result_a["summary"] == result_b["summary"]
    assert result_a["artifacts"] == result_b["artifacts"]
    for name in ARTIFACT_NAMES:
        assert (env_a["out"] / name).read_bytes() == (env_b["out"] / name).read_bytes()


def test_artifact_serialization_contract(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    run_norm(env)
    for name in ARTIFACT_NAMES:
        text = (env["out"] / name).read_text(encoding="utf-8")
        assert text.endswith("\n")
        parsed = json.loads(text)
        assert json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True) + "\n" == text


def test_artifacts_have_no_timestamp_path_or_hash(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    run_norm(env)
    workbook_hash = sha256_of_file(env["workbook"])
    for name in ARTIFACT_NAMES:
        text = (env["out"] / name).read_text(encoding="utf-8")
        assert "generatedAt" not in text and "timestamp" not in text
        assert str(tmp_path).lower() not in text.lower()
        assert "c:\\" not in text.lower() and "c:/" not in text.lower()
        assert workbook_hash not in text
        assert WORKBOOK_NAME not in text
        assert "=SUM" not in text


def test_rejected_cell_values_not_exposed(tmp_path: Path) -> None:
    rows = [
        ["TEST-HEADER-A", "TEST-HEADER-B", "TEST-HEADER-C"],
        ["TEST-ID-001", "TEST-NAME-001", "TEST-DO-NOT-LEAK-VALUE"],
    ]
    env = make_env(tmp_path, rows=rows)
    result = run_norm(env)
    assert result["summary"]["rejectedRecordCount"] == 1
    for name in ARTIFACT_NAMES:
        assert "TEST-DO-NOT-LEAK-VALUE" not in (env["out"] / name).read_text(
            encoding="utf-8"
        )
    for finding in result["findings"]:
        assert finding["actualValue"] is None


def test_console_does_not_leak_markers(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    env = make_env(tmp_path)
    argv = [
        str(env["workbook"]),
        "--manifest", str(env["manifest"]),
        "--source-base-dir", str(env["base"]),
        "--inspection-report", str(env["report"]),
        "--mapping-spec", str(env["spec"]),
        "--output-dir", str(tmp_path / "cli-out"),
    ]
    (tmp_path / "cli-out").mkdir()
    assert normalize_compendium.main(argv) == 0
    out = capsys.readouterr().out
    assert "TEST-ID-001" not in out
    assert "TEST-HEADER" not in out
    assert WORKBOOK_NAME not in out
    assert str(tmp_path).lower() not in out.lower()
    assert "internal-restricted" in out


def test_output_classification_is_internal_restricted(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    result = run_norm(env)
    assert result["classification"] == "internal-restricted"
    for name in ARTIFACT_NAMES:
        artifact = json.loads((env["out"] / name).read_text(encoding="utf-8"))
        assert artifact["classification"] == "internal-restricted"
