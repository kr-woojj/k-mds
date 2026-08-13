"""Restricted Normalizer — Reviewed Authorization Gate 통합 (ADR-0009/0010).

verified Manifest·verified Inspection Report·Reviewed Authorization Bundle
(Authorization + OutputRootBinding)·명시적 Mapping Specification을 요구하는
결정론적 Normalizer다.

- Authorization Validator의 필수 Flag(valid, reportIdentityMatched,
  sheetCoverageComplete, findingCoverageComplete, outputRootAuthorized,
  humanReviewCompleted)가 전부 true인 경우에만 Workbook을 연다.
- Mapping Spec의 Sheet는 authorizedSheetOrdinals에 포함되어야 한다.
- Medium Header Confidence의 자체 판단·우회 Option은 제공하지 않는다 —
  Header 승인 책임은 ADR-0010 Authorization에 있다.
- Authorization 실패 시 source_manifest_load, Workbook Open, Output Write를
  수행하지 않는다.
- 실제 산출물은 Internal Restricted Derived Data다 (ADR-0008).
- Console과 결과에 실제 Record, Cell, Header, Hash, Digest, Path를 출력하지
  않는다. 예외를 외부로 던지지 않는다.
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
from pathlib import Path
from typing import Any, Literal

import openpyxl  # type: ignore[import-untyped]
import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from validate_normalization_authorization import validate_authorization

from k_mds.models import (
    NormalizationAuthorization,
    ResultStatus,
    SheetClassification,
)
from k_mds.skills import source_manifest_load
from k_mds.skills.source_manifest_load import _StrictSafeLoader

CLASSIFICATION = "internal-restricted"
SUPPORTED_REPORT_VERSION = 1

ARTIFACT_RECORDS = "normalized-records.local.json"
ARTIFACT_FINDINGS = "normalization-findings.local.json"
ARTIFACT_EVIDENCE = "mapping-evidence.local.json"
ARTIFACT_SUMMARY = "normalization-summary.local.json"
ARTIFACT_NAMES = (ARTIFACT_RECORDS, ARTIFACT_FINDINGS, ARTIFACT_EVIDENCE, ARTIFACT_SUMMARY)

#: Authorization Validator가 전부 true를 반환해야 하는 필수 Flag (ADR-0010)
REQUIRED_AUTHORIZATION_FLAGS = (
    "valid",
    "reportIdentityMatched",
    "sheetCoverageComplete",
    "findingCoverageComplete",
    "outputRootAuthorized",
    "humanReviewCompleted",
)


class _MappingColumn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_column_ordinal: int = Field(ge=1)
    target_field: str = Field(min_length=1)
    required: bool
    value_type: Literal["string", "number", "integer", "boolean", "date"]


class _MappingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    dataset_id: str = Field(min_length=1)
    source_sheet_ordinal: int = Field(ge=0)
    header_row: int = Field(ge=1)
    first_data_row: int
    columns: list[_MappingColumn] = Field(min_length=1)

    @model_validator(mode="after")
    def _enforce_spec_invariants(self) -> _MappingSpec:
        if self.first_data_row <= self.header_row:
            raise ValueError("first_data_row는 header_row보다 커야 한다")
        ordinals = [column.source_column_ordinal for column in self.columns]
        if len(ordinals) != len(set(ordinals)):
            raise ValueError("중복 source_column_ordinal은 허용되지 않는다")
        fields = [column.target_field for column in self.columns]
        if len(fields) != len(set(fields)):
            raise ValueError("중복 target_field는 허용되지 않는다")
        return self


def _finding(
    severity: str, code: str, message: str, path: str | None = None
) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "path": path,
        "actualValue": None,
    }


def _failure(findings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "reportVersion": 1,
        "deterministic": True,
        "classification": CLASSIFICATION,
        "completed": False,
        "findings": findings,
        "artifacts": {},
        "summary": None,
    }


def serialize_artifact(data: dict[str, object]) -> str:
    """결정론적 직렬화: UTF-8, indent=2, sort_keys, 마지막 newline."""
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_artifacts_atomic(
    output_dir: Path, artifacts: dict[str, dict[str, object]]
) -> None:
    """모든 Artifact를 임시 파일에 작성한 뒤 Rename한다. 실패 시 전부 제거한다."""
    for name in artifacts:
        if (output_dir / name).exists():
            raise FileExistsError("existing output artifact")
    temp_paths: list[Path] = []
    renamed: list[Path] = []
    try:
        for name, data in artifacts.items():
            temp = output_dir / f"{name}.tmp"
            if temp.exists():
                raise FileExistsError("temporary artifact conflict")
            content = serialize_artifact(data)
            temp_paths.append(temp)
            with temp.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
        for name in artifacts:
            temp = output_dir / f"{name}.tmp"
            final = output_dir / name
            temp.rename(final)
            renamed.append(final)
    except BaseException:
        for temp in temp_paths:
            temp.unlink(missing_ok=True)
        for final in renamed:
            final.unlink(missing_ok=True)
        raise


def _find_git_root(path: Path) -> Path | None:
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _repository_root_candidate() -> Path:
    return Path(__file__).resolve().parents[1]


def _detect_repository_root() -> Path | None:
    """Normalizer Script 위치에서 Repository Root를 결정론적으로 탐지한다."""
    root = _repository_root_candidate()
    if (root / ".git").exists() and (root / "pyproject.toml").exists():
        return root
    return None


def _git_check(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, cwd=str(repo_root)
    )


def _validate_output_dir(
    output_dir: Path, input_dirs: list[Path]
) -> tuple[list[dict[str, Any]], Path | None]:
    """출력 Directory Boundary를 검증한다 (ADR-0008/0009, Defense-in-Depth)."""
    if not isinstance(output_dir, Path):
        return [_finding("ERROR", "OUTPUT_DIR_NOT_PATH", "output_dir는 Path여야 한다")], None
    lexical = output_dir if output_dir.is_absolute() else Path.cwd() / output_dir
    resolved = lexical.resolve()
    if not resolved.is_dir():
        return (
            [_finding("ERROR", "OUTPUT_DIR_NOT_FOUND", "output_dir가 존재하는 Directory가 아니다")],
            None,
        )

    for input_dir in input_dirs:
        if resolved == input_dir.resolve():
            return (
                [
                    _finding(
                        "ERROR",
                        "OUTPUT_PATH_CONFLICT",
                        "output_dir가 입력 Artifact Directory와 충돌한다",
                    )
                ],
                None,
            )

    repo_root = _find_git_root(lexical) or _find_git_root(resolved)
    if repo_root is not None:
        allowed_base = (repo_root / "data" / "normalized").resolve()
        if not resolved.is_relative_to(allowed_base):
            return (
                [
                    _finding(
                        "ERROR",
                        "OUTPUT_DIR_NOT_RESTRICTED",
                        "Repository 내부 출력은 data/normalized 아래만 허용된다",
                    )
                ],
                None,
            )
        rel = resolved.relative_to(repo_root).as_posix()
        # Directory 자체는 !normalized/**/ 규칙으로 재포함되므로
        # 실제로 생성될 Artifact 파일 경로 기준으로 Ignore 여부를 검사한다.
        ignored = (
            _git_check(
                repo_root, ["check-ignore", f"{rel}/{ARTIFACT_SUMMARY}"]
            ).returncode
            == 0
        )
        if not ignored:
            return (
                [
                    _finding(
                        "ERROR",
                        "OUTPUT_DIR_NOT_IGNORED",
                        "출력 Directory가 Git Ignore 상태가 아니다",
                    )
                ],
                None,
            )
        tracked = _git_check(repo_root, ["ls-files", "--", rel]).stdout.strip()
        if tracked:
            return (
                [
                    _finding(
                        "ERROR",
                        "OUTPUT_DIR_NOT_RESTRICTED",
                        "출력 Directory가 Git 추적 경로다",
                    )
                ],
                None,
            )
    return [], resolved


def _classify_cell(cell: Any) -> str:
    value = cell.value
    if value is None:
        return "blank"
    data_type = getattr(cell, "data_type", None)
    if data_type == "f":
        return "formula"
    if data_type == "e":
        return "error"
    if data_type == "b":
        return "boolean"
    if not isinstance(value, str) and getattr(cell, "is_date", False):
        return "date"
    if data_type == "n":
        return "number"
    if data_type in ("s", "str", "inlineStr"):
        return "string"
    return "unknown"


def _normalize_value(cell: Any, value_type: str) -> tuple[bool, Any, str | None]:
    """(성공 여부, 정규화 값, 오류 코드). 실제 Cell 값은 반환 코드에 포함하지 않는다."""
    category = _classify_cell(cell)
    if category == "formula":
        return False, None, "FORMULA_VALUE_PROHIBITED"
    if category == "error":
        return False, None, "ERROR_CELL_PROHIBITED"
    if category == "unknown":
        return False, None, "UNKNOWN_CELL_TYPE"
    value = cell.value
    if value is None:
        return True, None, None

    if value_type == "string":
        if not isinstance(value, str):
            return False, None, "VALUE_TYPE_MISMATCH"
        trimmed = value.strip()
        return True, trimmed if trimmed else None, None
    if value_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False, None, "VALUE_TYPE_MISMATCH"
        return True, value, None
    if value_type == "integer":
        if isinstance(value, bool):
            return False, None, "VALUE_TYPE_MISMATCH"
        if isinstance(value, int):
            return True, value, None
        if isinstance(value, float) and value.is_integer():
            return True, int(value), None
        return False, None, "VALUE_TYPE_MISMATCH"
    if value_type == "boolean":
        if not isinstance(value, bool):
            return False, None, "VALUE_TYPE_MISMATCH"
        return True, value, None
    if isinstance(value, datetime.datetime):
        return True, value.date().isoformat(), None
    if isinstance(value, datetime.date):
        return True, value.isoformat(), None
    return False, None, "VALUE_TYPE_MISMATCH"


def _load_json_object(path: Path) -> dict[str, Any] | None:
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def _check_inspection_compatibility(
    report: dict[str, Any], spec: _MappingSpec
) -> list[dict[str, Any]]:
    """구조 Compatibility만 검사한다 (ADR-0009 Amendment).

    normalizationReady·Header Confidence·Finding Severity·Scan Limit·Human
    Review의 실행 승인 판단은 ADR-0010 Authorization Validator의 책임이다.
    Inspector의 summary.normalizationReady는 Technical Hint(Audit Metadata)로만
    보존하며 실행 조건으로 사용하지 않는다. Sheet는 List Index가 아니라
    sheetOrdinal Key로 조회한다.
    """
    if report.get("reportVersion") != SUPPORTED_REPORT_VERSION:
        return [
            _finding(
                "ERROR", "INSPECTION_REPORT_INVALID", "지원하지 않는 Inspection Report Version이다"
            )
        ]
    summary = report.get("summary")
    if not isinstance(summary, dict):
        return [
            _finding("ERROR", "INSPECTION_REPORT_INVALID", "Inspection Report summary가 없다")
        ]
    sheets = report.get("sheets")
    if not isinstance(sheets, list):
        return [
            _finding("ERROR", "INSPECTION_REPORT_INVALID", "Inspection Report sheets가 없다")
        ]

    findings: list[dict[str, Any]] = []
    sheet_by_ordinal: dict[int, dict[str, Any]] = {}
    for item in sheets:
        if not isinstance(item, dict):
            findings.append(
                _finding(
                    "ERROR",
                    "INSPECTION_REPORT_INVALID",
                    "Report Sheet Item은 Object여야 한다",
                    "$.report.sheets",
                )
            )
            continue
        ordinal = item.get("sheetOrdinal")
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
            findings.append(
                _finding(
                    "ERROR",
                    "INSPECTION_SHEET_ORDINAL_INVALID",
                    "Report sheetOrdinal은 0 이상의 정수여야 한다",
                    "$.report.sheets",
                )
            )
            continue
        if ordinal in sheet_by_ordinal:
            findings.append(
                _finding(
                    "ERROR",
                    "INSPECTION_SHEET_ORDINAL_DUPLICATE",
                    "Report sheetOrdinal이 중복된다",
                    "$.report.sheets",
                )
            )
            continue
        sheet_by_ordinal[ordinal] = item
    if findings:
        return findings

    sheet = sheet_by_ordinal.get(spec.source_sheet_ordinal)
    if sheet is None:
        return [
            _finding(
                "ERROR",
                "INSPECTION_SHEET_OUT_OF_RANGE",
                "Mapping Spec의 source_sheet_ordinal이 Report에 존재하지 않는다",
                "$.mappingSpec.source_sheet_ordinal",
            )
        ]
    if sheet.get("inferredHeaderRow") != spec.header_row:
        return [
            _finding(
                "ERROR",
                "INSPECTION_HEADER_MISMATCH",
                "Mapping Spec의 header_row가 Inspection 결과와 일치하지 않는다",
                "$.mappingSpec.header_row",
            )
        ]
    return []


def _check_authorization_gate(
    *,
    inspection_report: dict[str, Any],
    inspection_report_bytes: bytes,
    authorization: dict[str, Any],
    output_root_binding: dict[str, Any],
    output_dir: Path,
    repository_root: Path,
) -> tuple[list[dict[str, Any]], list[int]]:
    """Authorization Validator를 호출하고 필수 Flag를 전부 확인한다.

    Validator의 실제 Finding Message는 복사하지 않고 Code Category와 Count만
    Normalizer Finding에 요약한다.
    """
    try:
        result = validate_authorization(
            inspection_report=inspection_report,
            inspection_report_bytes=inspection_report_bytes,
            authorization=authorization,
            output_root_binding=output_root_binding,
            output_dir=output_dir,
            repository_root=repository_root,
        )
    except Exception:  # noqa: BLE001 — 예외를 정규화한다
        return (
            [
                _finding(
                    "ERROR",
                    "AUTHORIZATION_VALIDATION_FAILED",
                    "Authorization Validator 실행이 실패했다",
                    "$.authorization",
                )
            ],
            [],
        )

    findings: list[dict[str, Any]] = []
    for flag in REQUIRED_AUTHORIZATION_FLAGS:
        if flag not in result:
            findings.append(
                _finding(
                    "ERROR",
                    "AUTHORIZATION_FLAG_MISSING",
                    f"Authorization Validator 결과에 {flag} Flag가 없다",
                    "$.authorization",
                )
            )
        elif result[flag] is not True:
            findings.append(
                _finding(
                    "ERROR",
                    "AUTHORIZATION_VALIDATION_FAILED",
                    f"Authorization 필수 Flag {flag}가 승인되지 않았다",
                    "$.authorization",
                )
            )

    validator_findings = result.get("findings")
    validator_findings = (
        validator_findings if isinstance(validator_findings, list) else []
    )
    code_counts: dict[str, int] = {}
    for item in validator_findings:
        code = str(item.get("code")) if isinstance(item, dict) else "UNKNOWN"
        code_counts[code] = code_counts.get(code, 0) + 1
    for code in sorted(code_counts):
        findings.append(
            _finding(
                "ERROR",
                "AUTHORIZATION_VALIDATION_FAILED",
                f"Authorization 검증 실패 Category: {code} (count={code_counts[code]})",
                "$.authorization",
            )
        )

    ordinals_raw = result.get("authorizedSheetOrdinals")
    ordinals = [
        item
        for item in (ordinals_raw if isinstance(ordinals_raw, list) else [])
        if isinstance(item, int)
    ]
    return findings, sorted(ordinals)


def normalize_compendium(
    *,
    workbook_path: Path,
    manifest_path: Path,
    source_base_dir: Path,
    inspection_report_path: Path,
    authorization_path: Path,
    output_root_binding_path: Path,
    mapping_spec_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    """Reviewed Authorization Bundle이 승인된 입력만 Restricted Artifact로 정규화한다."""
    for label, candidate in (
        ("workbookPath", workbook_path),
        ("manifestPath", manifest_path),
        ("sourceBaseDir", source_base_dir),
        ("inspectionReportPath", inspection_report_path),
        ("authorizationPath", authorization_path),
        ("outputRootBindingPath", output_root_binding_path),
        ("mappingSpecPath", mapping_spec_path),
    ):
        if not isinstance(candidate, Path):
            return _failure(
                [
                    _finding(
                        "ERROR", "INPUT_PATH_NOT_PATH", "입력 경로는 Path여야 한다", f"$.{label}"
                    )
                ]
            )
    for label, candidate, missing_code in (
        ("workbookPath", workbook_path, "INPUT_FILE_NOT_FOUND"),
        ("manifestPath", manifest_path, "INPUT_FILE_NOT_FOUND"),
        ("inspectionReportPath", inspection_report_path, "INPUT_FILE_NOT_FOUND"),
        ("authorizationPath", authorization_path, "AUTHORIZATION_FILE_NOT_FOUND"),
        (
            "outputRootBindingPath",
            output_root_binding_path,
            "OUTPUT_ROOT_BINDING_FILE_NOT_FOUND",
        ),
        ("mappingSpecPath", mapping_spec_path, "INPUT_FILE_NOT_FOUND"),
    ):
        if not candidate.is_file():
            return _failure(
                [_finding("ERROR", missing_code, "필수 입력 파일이 존재하지 않는다", f"$.{label}")]
            )

    output_findings, resolved_output = _validate_output_dir(
        output_dir,
        [
            workbook_path.parent,
            manifest_path.parent,
            inspection_report_path.parent,
            mapping_spec_path.parent,
        ],
    )
    if output_findings or resolved_output is None:
        return _failure(output_findings)

    repository_root = _detect_repository_root()
    if repository_root is None:
        return _failure(
            [
                _finding(
                    "ERROR",
                    "REPOSITORY_ROOT_NOT_FOUND",
                    "Repository Root를 결정론적으로 탐지할 수 없다",
                )
            ]
        )

    try:
        inspection_report_bytes = inspection_report_path.read_bytes()
    except OSError:
        return _failure(
            [_finding("ERROR", "INSPECTION_REPORT_INVALID", "Inspection Report를 읽을 수 없다")]
        )
    report = _load_json_object(inspection_report_path)
    if report is None:
        return _failure(
            [
                _finding(
                    "ERROR",
                    "INSPECTION_REPORT_INVALID",
                    "Inspection Report가 유효한 JSON Object가 아니다",
                )
            ]
        )
    authorization = _load_json_object(authorization_path)
    if authorization is None:
        return _failure(
            [
                _finding(
                    "ERROR",
                    "AUTHORIZATION_JSON_INVALID",
                    "Authorization이 유효한 JSON Object가 아니다",
                )
            ]
        )
    output_root_binding = _load_json_object(output_root_binding_path)
    if output_root_binding is None:
        return _failure(
            [
                _finding(
                    "ERROR",
                    "OUTPUT_ROOT_BINDING_JSON_INVALID",
                    "Output Root Binding이 유효한 JSON Object가 아니다",
                )
            ]
        )

    # --- Authorization Gate: 실패 시 Manifest·Workbook·Output I/O를 수행하지 않는다 ---
    gate_findings, authorized_ordinals = _check_authorization_gate(
        inspection_report=report,
        inspection_report_bytes=inspection_report_bytes,
        authorization=authorization,
        output_root_binding=output_root_binding,
        output_dir=resolved_output,
        repository_root=repository_root,
    )
    if gate_findings:
        return _failure(gate_findings)

    try:
        raw_spec: Any = yaml.load(  # noqa: S506 — SafeLoader 기반
            mapping_spec_path.read_text(encoding="utf-8"), Loader=_StrictSafeLoader
        )
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return _failure(
            [_finding("ERROR", "MAPPING_SPEC_INVALID", "Mapping Spec이 유효한 YAML이 아니다")]
        )
    try:
        spec = _MappingSpec.model_validate(raw_spec)
    except ValidationError as exc:
        return _failure(
            [
                _finding("ERROR", "MAPPING_SPEC_INVALID", str(error["msg"]), "$.mappingSpec")
                for error in exc.errors(
                    include_url=False, include_input=False, include_context=False
                )
            ]
        )

    # --- Mapping Sheet Authorization ---
    if spec.source_sheet_ordinal not in authorized_ordinals:
        return _failure(
            [
                _finding(
                    "ERROR",
                    "MAPPING_SHEET_NOT_AUTHORIZED",
                    "Mapping Spec의 Sheet가 authorizedSheetOrdinals에 포함되지 않는다",
                    "$.mappingSpec.source_sheet_ordinal",
                )
            ]
        )
    try:
        auth_model = NormalizationAuthorization.model_validate(authorization)
    except ValidationError:
        return _failure(
            [
                _finding(
                    "ERROR",
                    "AUTHORIZATION_VALIDATION_FAILED",
                    "Authorization 구조가 유효하지 않다",
                    "$.authorization",
                )
            ]
        )
    auth_sheet = next(
        (
            sheet
            for sheet in auth_model.sheets
            if sheet.sheet_ordinal == spec.source_sheet_ordinal
        ),
        None,
    )
    if (
        auth_sheet is None
        or auth_sheet.classification is not SheetClassification.DATA_TABLE
    ):
        return _failure(
            [
                _finding(
                    "ERROR",
                    "MAPPING_SHEET_NOT_AUTHORIZED",
                    "Mapping Sheet는 data_table로 승인되어야 한다",
                    "$.mappingSpec.source_sheet_ordinal",
                )
            ]
        )
    if auth_sheet.header_row != spec.header_row:
        return _failure(
            [
                _finding(
                    "ERROR",
                    "AUTHORIZATION_HEADER_MISMATCH",
                    "Mapping Spec header_row가 Authorization 승인값과 일치하지 않는다",
                    "$.mappingSpec.header_row",
                )
            ]
        )

    inspection_findings = _check_inspection_compatibility(report, spec)
    if inspection_findings:
        return _failure(inspection_findings)
    report_source_id = str(report.get("sourceId"))

    manifest_result = source_manifest_load(manifest_path, base_dir=source_base_dir)
    if manifest_result.status is not ResultStatus.PASS:
        return _failure(
            [
                _finding(
                    "ERROR",
                    "MANIFEST_VERIFICATION_FAILED",
                    "Source Manifest 검증이 실패했다",
                    "$.manifestPath",
                )
            ]
        )
    matched_source_id: str | None = None
    base_resolved = source_base_dir.resolve()
    for source in manifest_result.data["sources"]:
        if (base_resolved / str(source["source_file"])).resolve() == workbook_path.resolve():
            matched_source_id = str(source["source_id"])
            break
    if matched_source_id is None:
        return _failure(
            [
                _finding(
                    "ERROR",
                    "WORKBOOK_NOT_IN_MANIFEST",
                    "Workbook이 검증된 Source Entry와 일치하지 않는다",
                )
            ]
        )
    if matched_source_id != report_source_id:
        return _failure(
            [
                _finding(
                    "ERROR",
                    "SOURCE_ID_MISMATCH",
                    "Manifest source_id와 Inspection Report sourceId가 일치하지 않는다",
                )
            ]
        )

    # --- Row 처리 (read-only) ---
    try:
        workbook = openpyxl.load_workbook(
            filename=workbook_path, read_only=True, data_only=False, keep_links=False
        )
    except Exception:  # noqa: BLE001 — 예외를 정규화한다
        return _failure(
            [_finding("ERROR", "WORKBOOK_LOAD_FAILED", "Workbook을 read-only로 열 수 없다")]
        )

    records: list[dict[str, Any]] = []
    row_findings: list[dict[str, Any]] = []
    mapped_counts = dict.fromkeys((column.target_field for column in spec.columns), 0)
    rejected_counts = dict.fromkeys((column.target_field for column in spec.columns), 0)
    source_record_count = 0
    rejected_record_count = 0
    try:
        worksheet = workbook.worksheets[spec.source_sheet_ordinal]
        max_needed_column = max(column.source_column_ordinal for column in spec.columns)
        sheet_ordinal = spec.source_sheet_ordinal
        for row_offset, row in enumerate(
            worksheet.iter_rows(min_row=spec.first_data_row, max_col=max_needed_column)
        ):
            row_ordinal = spec.first_data_row + row_offset
            cells = {
                column.source_column_ordinal: row[column.source_column_ordinal - 1]
                for column in spec.columns
                if column.source_column_ordinal <= len(row)
            }
            if all(cell is None or cell.value is None for cell in cells.values()):
                continue
            source_record_count += 1

            values: dict[str, Any] = {}
            row_rejected = False
            for column in spec.columns:
                cell = cells.get(column.source_column_ordinal)
                if cell is None:
                    ok, value, code = True, None, None
                else:
                    ok, value, code = _normalize_value(cell, column.value_type)
                if ok and value is None and column.required:
                    ok, code = False, "REQUIRED_VALUE_MISSING"
                if not ok:
                    row_rejected = True
                    rejected_counts[column.target_field] += 1
                    row_findings.append(
                        _finding(
                            "WARNING",
                            code or "VALUE_TYPE_MISMATCH",
                            "Row가 Normalization 규칙을 만족하지 않아 거부되었다",
                            f"$.sheets.{sheet_ordinal}.rows.{row_ordinal}"
                            f".columns.{column.source_column_ordinal}",
                        )
                    )
                    continue
                values[column.target_field] = value

            if row_rejected:
                rejected_record_count += 1
                continue
            for column in spec.columns:
                if values.get(column.target_field) is not None:
                    mapped_counts[column.target_field] += 1
            records.append(
                {
                    "recordOrdinal": len(records),
                    "datasetId": spec.dataset_id,
                    "sourceId": matched_source_id,
                    "sourceSheetOrdinal": sheet_ordinal,
                    "sourceRowOrdinal": row_ordinal,
                    "values": values,
                }
            )
    finally:
        workbook.close()

    summary = {
        "reportVersion": 1,
        "deterministic": True,
        "classification": CLASSIFICATION,
        "sourceId": matched_source_id,
        "datasetId": spec.dataset_id,
        "sourceRecordCount": source_record_count,
        "normalizedRecordCount": len(records),
        "rejectedRecordCount": rejected_record_count,
        "findingCount": len(row_findings),
        "humanReviewRequired": rejected_record_count > 0 or bool(row_findings),
    }
    common = {
        "reportVersion": 1,
        "deterministic": True,
        "classification": CLASSIFICATION,
        "datasetId": spec.dataset_id,
        "sourceId": matched_source_id,
    }
    artifacts: dict[str, dict[str, object]] = {
        ARTIFACT_RECORDS: {**common, "records": records},
        ARTIFACT_FINDINGS: {**common, "findings": row_findings},
        ARTIFACT_EVIDENCE: {
            **common,
            "columns": [
                {
                    "datasetId": spec.dataset_id,
                    "sourceId": matched_source_id,
                    "sourceSheetOrdinal": spec.source_sheet_ordinal,
                    "sourceColumnOrdinal": column.source_column_ordinal,
                    "targetField": column.target_field,
                    "valueType": column.value_type,
                    "required": column.required,
                    "mappedRecordCount": mapped_counts[column.target_field],
                    "rejectedRecordCount": rejected_counts[column.target_field],
                }
                for column in spec.columns
            ],
        },
        ARTIFACT_SUMMARY: summary,
    }

    try:
        write_artifacts_atomic(resolved_output, artifacts)
    except FileExistsError as exc:
        code = "OUTPUT_ALREADY_EXISTS" if "existing" in str(exc) else "OUTPUT_WRITE_FAILED"
        return _failure(
            [_finding("ERROR", code, "Output Artifact를 작성할 수 없다", "$.outputDir")]
        )
    except Exception:  # noqa: BLE001 — 예외를 정규화한다
        return _failure(
            [_finding("ERROR", "OUTPUT_WRITE_FAILED", "Atomic Write가 실패했다", "$.outputDir")]
        )

    return {
        "reportVersion": 1,
        "deterministic": True,
        "classification": CLASSIFICATION,
        "completed": True,
        "findings": row_findings,
        "artifacts": artifacts,
        "summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="normalize_compendium.py",
        description="deterministic restricted normalizer with reviewed authorization",
    )
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-base-dir", type=Path, required=True)
    parser.add_argument("--inspection-report", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--output-root-binding", type=Path, required=True)
    parser.add_argument("--mapping-spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    result = normalize_compendium(
        workbook_path=args.workbook,
        manifest_path=args.manifest,
        source_base_dir=args.source_base_dir,
        inspection_report_path=args.inspection_report,
        authorization_path=args.authorization,
        output_root_binding_path=args.output_root_binding,
        mapping_spec_path=args.mapping_spec,
        output_dir=args.output_dir,
    )
    # Console에는 Count·ID·Path·Hash를 출력하지 않는다 (ADR-0009 Amendment).
    # 실제 Count는 internal-restricted Summary Artifact에만 존재한다.
    completed = result.get("completed") is True
    summary = result.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    human_review = (
        bool(summary.get("humanReviewRequired", True)) if completed else True
    )
    print(
        "[normalize] "
        f"completed={completed} "
        f"classification={result.get('classification')} "
        f"artifactSetCreated={completed} "
        f"humanReviewRequired={human_review}"
    )
    return 0 if completed else 1


if __name__ == "__main__":
    raise SystemExit(main())
