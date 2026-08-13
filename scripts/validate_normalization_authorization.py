"""Normalization Authorization Validator (ADR-0010 + Amendment).

Inspection Report 원 Byte Identity, 전체 Sheet Coverage, Finding 집합의 정확한
일치, Output Root Binding까지 결정론적으로 검증한다.

- 현재 Report의 Blocking Finding은 resolved로 자기선언할 수 없다
  (CURRENT_REPORT_BLOCKING_FINDING) — Inspector 재실행으로만 해소한다.
- Reviewable Finding은 현재 Report에서 accepted_for_reviewed_scope만 허용한다.
- Unknown Finding은 항상 Blocking이다.
- Sheet 이름, Header 문자열, 실제 Path, Digest, 승인자 정보, Timestamp를
  결과와 Console에 포함하지 않는다. 예외를 외부로 던지지 않는다.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from k_mds.models import (
    FindingDisposition,
    NormalizationAuthorization,
    OutputRootBinding,
    SheetClassification,
)

SUPPORTED_REPORT_VERSION = 1
CLASSIFICATION = "internal-restricted"

#: ADR-0010 Finding Classification
BLOCKING_CODES = {
    "WORKBOOK_SCAN_LIMIT_REACHED",
    "WORKBOOK_HEADER_NOT_DETECTED",
    "WORKBOOK_XML_PART_SCAN_SKIPPED",
}
REVIEWABLE_CODES = {
    "WORKBOOK_DECLARED_DIMENSION_EXCESSIVE",
    "WORKBOOK_PROTECTION_ENABLED",
    "WORKBOOK_CUSTOM_XML_PRESENT",
    "WORKBOOK_DIGITAL_SIGNATURE_PRESENT",
    "WORKBOOK_EMPTY_SHEET",
}

#: Empty Sheet에 허용되는 Authorization Classification (ADR-0010 Amendment)
_EMPTY_SHEET_ALLOWED_CLASSIFICATIONS = (
    SheetClassification.METADATA_OR_README,
    SheetClassification.EXCLUDED_NON_DATA,
)

_ARTIFACT_PROBE = "normalization-summary.local.json"


def compute_inspection_report_id(report_bytes: bytes) -> str:
    """Inspection Report 원 Byte의 SHA-256 lowercase hex Identity."""
    return hashlib.sha256(report_bytes).hexdigest()


def _finding(code: str, message: str, path: str | None = None) -> dict[str, Any]:
    return {
        "severity": "ERROR",
        "code": code,
        "message": message,
        "path": path,
        "actualValue": None,
    }


def _git_check(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, cwd=str(repo_root)
    )


def _sheet_ordinal_from_path(path: object) -> int | None:
    if not isinstance(path, str):
        return None
    match = re.search(r"\$\.sheets\.(\d+)", path)
    return int(match.group(1)) if match else None


def validate_output_root_binding(
    *,
    authorization: NormalizationAuthorization,
    binding: OutputRootBinding,
    output_dir: object,
    repository_root: object,
) -> list[dict[str, Any]]:
    """Output Root Binding 정책을 검증한다. 실제 Path는 Finding에 포함하지 않는다."""
    findings: list[dict[str, Any]] = []
    if authorization.approved_output_root_id != binding.root_id:
        findings.append(
            _finding(
                "OUTPUT_ROOT_ID_MISMATCH",
                "Binding rootId가 승인된 Output Root ID와 일치하지 않는다",
                "$.binding.rootId",
            )
        )
    if not isinstance(output_dir, Path):
        findings.append(
            _finding("OUTPUT_DIR_NOT_PATH", "output_dir는 Path여야 한다", "$.outputDir")
        )
        return findings
    if not isinstance(repository_root, Path):
        findings.append(
            _finding(
                "OUTPUT_ROOT_BINDING_INVALID",
                "repository_root는 Path여야 한다",
                "$.repositoryRoot",
            )
        )
        return findings
    if not output_dir.is_dir():
        findings.append(
            _finding(
                "OUTPUT_DIR_NOT_FOUND",
                "output_dir가 존재하는 Directory가 아니다",
                "$.outputDir",
            )
        )
        return findings

    root_resolved = Path(binding.root_path).resolve()
    output_resolved = output_dir.resolve()
    if not output_resolved.is_relative_to(root_resolved):
        findings.append(
            _finding(
                "OUTPUT_DIR_OUTSIDE_APPROVED_ROOT",
                "output_dir가 승인된 Root 아래에 있지 않다 (Symlink Resolve 포함)",
                "$.outputDir",
            )
        )
        return findings

    repo_resolved = repository_root.resolve()
    if output_resolved.is_relative_to(repo_resolved):
        allowed = (repo_resolved / "data" / "normalized").resolve()
        if not output_resolved.is_relative_to(allowed):
            findings.append(
                _finding(
                    "OUTPUT_DIR_NOT_RESTRICTED",
                    "Repository 내부 출력은 data/normalized 아래만 허용된다",
                    "$.outputDir",
                )
            )
            return findings
        rel = output_resolved.relative_to(repo_resolved).as_posix()
        ignore_check = _git_check(
            repo_resolved, ["check-ignore", f"{rel}/{_ARTIFACT_PROBE}"]
        )
        if ignore_check.returncode != 0:
            findings.append(
                _finding(
                    "OUTPUT_DIR_NOT_IGNORED",
                    "출력 Directory가 Git Ignore 상태가 아니다",
                    "$.outputDir",
                )
            )
        if _git_check(repo_resolved, ["ls-files", "--", rel]).stdout.strip():
            findings.append(
                _finding(
                    "OUTPUT_DIR_TRACKED",
                    "출력 Directory에 Git 추적 파일이 있다",
                    "$.outputDir",
                )
            )
        if _git_check(
            repo_resolved, ["diff", "--cached", "--name-only", "--", rel]
        ).stdout.strip():
            findings.append(
                _finding(
                    "OUTPUT_DIR_STAGED",
                    "출력 Directory에 Staged 파일이 있다",
                    "$.outputDir",
                )
            )
    return findings


def _result(
    *,
    valid: bool,
    authorized: list[int],
    sheet_coverage: bool,
    finding_coverage: bool,
    identity_matched: bool,
    output_root_authorized: bool,
    blocking: int,
    reviewed: int,
    human_review: bool,
    findings: list[dict[str, Any]],
) -> dict[str, object]:
    return {
        "valid": valid,
        "classification": CLASSIFICATION,
        "authorizedSheetOrdinals": authorized,
        "sheetCoverageComplete": sheet_coverage,
        "findingCoverageComplete": finding_coverage,
        "reportIdentityMatched": identity_matched,
        "outputRootAuthorized": output_root_authorized,
        "blockingFindingCount": blocking,
        "reviewedFindingCount": reviewed,
        "humanReviewCompleted": human_review,
        "findings": findings,
    }


def _fail(
    findings: list[dict[str, Any]],
    *,
    blocking: int = 0,
    human_review: bool = False,
    identity_matched: bool = False,
) -> dict[str, object]:
    return _result(
        valid=False,
        authorized=[],
        sheet_coverage=False,
        finding_coverage=False,
        identity_matched=identity_matched,
        output_root_authorized=False,
        blocking=blocking,
        reviewed=0,
        human_review=human_review,
        findings=findings,
    )


def validate_authorization(
    *,
    inspection_report: dict[str, object],
    inspection_report_bytes: bytes,
    authorization: dict[str, object],
    output_root_binding: dict[str, object] | None = None,
    output_dir: Path | None = None,
    repository_root: Path | None = None,
) -> dict[str, object]:
    """Report Identity·Sheet Coverage·Finding 집합·Output Binding을 검증한다."""
    if not isinstance(inspection_report_bytes, (bytes, bytearray)):
        return _fail(
            [_finding("REPORT_BYTES_INVALID", "inspection_report_bytes는 bytes여야 한다", "$")]
        )
    if not isinstance(inspection_report, dict):
        return _fail(
            [_finding("REPORT_NOT_OBJECT", "Inspection Report는 JSON Object여야 한다", "$")]
        )
    if not isinstance(authorization, dict):
        return _fail(
            [_finding("AUTHORIZATION_NOT_OBJECT", "Authorization은 JSON Object여야 한다", "$")]
        )

    try:
        auth = NormalizationAuthorization.model_validate(authorization)
    except ValidationError as exc:
        return _fail(
            [
                _finding("AUTHORIZATION_INVALID", str(error["msg"]), "$.authorization")
                for error in exc.errors(
                    include_url=False, include_input=False, include_context=False
                )
            ]
        )

    findings: list[dict[str, Any]] = []

    # --- Report Identity (원 Byte Digest, 상수시간 비교) ---
    computed_id = compute_inspection_report_id(bytes(inspection_report_bytes))
    identity_matched = hmac.compare_digest(computed_id, auth.inspection_report_id)
    if not identity_matched:
        findings.append(
            _finding(
                "INSPECTION_REPORT_ID_MISMATCH",
                "Authorization이 현재 Inspection Report Byte와 결합되어 있지 않다",
                "$.authorization.inspectionReportId",
            )
        )

    if inspection_report.get("reportVersion") != SUPPORTED_REPORT_VERSION:
        findings.append(
            _finding(
                "REPORT_VERSION_UNSUPPORTED",
                "지원하지 않는 Inspection Report Version이다",
                "$.report.reportVersion",
            )
        )
        return _fail(
            findings,
            human_review=auth.human_review_completed,
            identity_matched=identity_matched,
        )

    summary = inspection_report.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    if (
        inspection_report.get("provenanceVerified") is not True
        or inspection_report.get("manifestStatus") != "verified"
        or inspection_report.get("inspectionMode") != "verified-source"
        or summary.get("inspectionCompleted") is not True
    ):
        findings.append(
            _finding(
                "REPORT_NOT_VERIFIED", "Inspection Report가 verified 상태가 아니다", "$.report"
            )
        )
        return _fail(
            findings,
            human_review=auth.human_review_completed,
            identity_matched=identity_matched,
        )

    if inspection_report.get("sourceId") != auth.source_id:
        findings.append(
            _finding(
                "SOURCE_ID_MISMATCH",
                "Authorization sourceId가 Inspection Report와 일치하지 않는다",
                "$.authorization.sourceId",
            )
        )

    # --- 전체 Sheet Coverage ---
    report_sheets_raw = inspection_report.get("sheets")
    report_sheets_raw = report_sheets_raw if isinstance(report_sheets_raw, list) else []
    report_sheet_by_ordinal: dict[int, dict[str, Any]] = {}
    report_ordinals: list[int] = []
    for item in report_sheets_raw:
        item = item if isinstance(item, dict) else {}
        ordinal = item.get("sheetOrdinal")
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
            findings.append(
                _finding(
                    "REPORT_SHEET_ORDINAL_INVALID",
                    "Report sheetOrdinal은 0 이상의 정수여야 한다",
                    "$.report.sheets",
                )
            )
            continue
        if ordinal in report_sheet_by_ordinal:
            findings.append(
                _finding(
                    "REPORT_SHEET_ORDINAL_DUPLICATE",
                    "Report sheetOrdinal이 중복된다",
                    "$.report.sheets",
                )
            )
            continue
        report_sheet_by_ordinal[ordinal] = item
        report_ordinals.append(ordinal)

    auth_ordinals = {sheet.sheet_ordinal for sheet in auth.sheets}
    report_ordinal_set = set(report_ordinals)
    for missing in sorted(report_ordinal_set - auth_ordinals):
        findings.append(
            _finding(
                "SHEET_AUTHORIZATION_MISSING",
                f"Report sheetOrdinal {missing}에 대한 분류 승인이 없다",
                "$.authorization.sheets",
            )
        )
    for extra in sorted(auth_ordinals - report_ordinal_set):
        findings.append(
            _finding(
                "SHEET_AUTHORIZATION_EXTRA",
                f"Report에 존재하지 않는 sheetOrdinal {extra}가 승인되었다",
                "$.authorization.sheets",
            )
        )
    sheet_coverage = report_ordinal_set == auth_ordinals and bool(report_ordinal_set)

    # --- data_table Sheet의 Header 정합성 ---
    for sheet in auth.sheets:
        if sheet.classification is not SheetClassification.DATA_TABLE:
            continue
        report_sheet = report_sheet_by_ordinal.get(sheet.sheet_ordinal)
        if report_sheet is None:
            continue
        if report_sheet.get("inferredHeaderRow") != sheet.header_row:
            findings.append(
                _finding(
                    "HEADER_ROW_MISMATCH",
                    f"sheetOrdinal {sheet.sheet_ordinal}의 header_row가 Inspection과 다르다",
                    f"$.authorization.sheets.{sheet.sheet_ordinal}.headerRow",
                )
            )
        if report_sheet.get("headerConfidence") != sheet.header_confidence.value:
            findings.append(
                _finding(
                    "HEADER_CONFIDENCE_MISMATCH",
                    f"sheetOrdinal {sheet.sheet_ordinal}의 headerConfidence가 Inspection과 다르다",
                    f"$.authorization.sheets.{sheet.sheet_ordinal}.headerConfidence",
                )
            )

    # --- Finding 집합의 정확한 일치와 처분 정책 ---
    report_findings_raw = inspection_report.get("findings")
    report_findings_raw = (
        report_findings_raw if isinstance(report_findings_raw, list) else []
    )
    report_keys: list[tuple[str, int | None]] = []
    blocking_count = 0
    reviewed_count = 0
    seen_keys: set[tuple[str, int | None]] = set()
    ack_by_key = {
        (item.code, item.sheet_ordinal): item for item in auth.acknowledged_findings
    }
    for item in report_findings_raw:
        if not isinstance(item, dict):
            findings.append(
                _finding("REPORT_NOT_OBJECT", "Inspection Finding이 Object가 아니다", "$.report")
            )
            continue
        code = str(item.get("code"))
        ordinal = _sheet_ordinal_from_path(item.get("path"))
        key = (code, ordinal)
        if key in seen_keys:
            findings.append(
                _finding(
                    "REPORT_FINDING_DUPLICATE",
                    "Report Finding Key가 중복된다",
                    "$.report.findings",
                )
            )
            continue
        seen_keys.add(key)
        report_keys.append(key)

        is_fatal = item.get("severity") == "ERROR"
        if is_fatal:
            blocking_count += 1
            findings.append(
                _finding(
                    "FATAL_FINDING_PRESENT",
                    "Fatal ERROR Finding은 Authorization으로 승인할 수 없다",
                    "$.report.findings",
                )
            )
            continue
        if code in BLOCKING_CODES:
            # 현재 Report의 Blocking Finding은 어떤 처분으로도 승인할 수 없다.
            blocking_count += 1
            findings.append(
                _finding(
                    "CURRENT_REPORT_BLOCKING_FINDING",
                    "현재 Report의 Blocking Finding은 Inspector 재실행으로만 해소할 수 있다",
                    "$.report.findings",
                )
            )
            continue
        ack = ack_by_key.get(key)
        if ack is None:
            blocking_count += 1
            findings.append(
                _finding(
                    "FINDING_AUTHORIZATION_MISSING",
                    "Inspection Finding에 대한 Authorization이 없다",
                    "$.authorization.acknowledgedFindings",
                )
            )
            continue
        if code in REVIEWABLE_CODES:
            if ack.disposition is FindingDisposition.ACCEPTED_FOR_REVIEWED_SCOPE:
                reviewed_count += 1
            else:
                blocking_count += 1
                findings.append(
                    _finding(
                        "BLOCKING_FINDING_UNRESOLVED",
                        "현재 Report의 Reviewable Finding은 "
                        "accepted_for_reviewed_scope만 허용된다",
                        "$.authorization.acknowledgedFindings",
                    )
                )
            continue
        blocking_count += 1
        findings.append(
            _finding(
                "UNKNOWN_FINDING_BLOCKING",
                "Policy에 정의되지 않은 Finding은 기본 blocking이다",
                "$.authorization.acknowledgedFindings",
            )
        )

    # Empty Sheet는 metadata_or_readme 또는 excluded_non_data로만 분류할 수 있다.
    auth_sheet_by_ordinal = {sheet.sheet_ordinal: sheet for sheet in auth.sheets}
    empty_ordinals = sorted(
        ordinal
        for code, ordinal in report_keys
        if code == "WORKBOOK_EMPTY_SHEET" and ordinal is not None
    )
    for ordinal in empty_ordinals:
        empty_sheet = auth_sheet_by_ordinal.get(ordinal)
        if empty_sheet is not None and (
            empty_sheet.classification not in _EMPTY_SHEET_ALLOWED_CLASSIFICATIONS
        ):
            findings.append(
                _finding(
                    "EMPTY_SHEET_CLASSIFICATION_INVALID",
                    f"Empty Sheet(sheetOrdinal {ordinal})는 metadata_or_readme 또는 "
                    "excluded_non_data로만 분류할 수 있다",
                    f"$.authorization.sheets.{ordinal}",
                )
            )

    report_key_set = set(report_keys)
    for _stale_key in sorted(
        (key for key in ack_by_key if key not in report_key_set),
        key=lambda item: (item[0], -1 if item[1] is None else item[1]),
    ):
        findings.append(
            _finding(
                "FINDING_AUTHORIZATION_STALE",
                "현재 Report에 존재하지 않는 Finding이 승인되어 있다",
                "$.authorization.acknowledgedFindings",
            )
        )
    finding_coverage = (
        set(ack_by_key) == report_key_set
        if report_key_set or ack_by_key
        else True
    )

    # --- Output Root Binding (선택 입력) ---
    output_root_authorized = False
    if output_root_binding is not None:
        if not isinstance(output_root_binding, dict):
            findings.append(
                _finding(
                    "OUTPUT_ROOT_BINDING_INVALID",
                    "Output Root Binding은 JSON Object여야 한다",
                    "$.binding",
                )
            )
        else:
            try:
                binding = OutputRootBinding.model_validate(output_root_binding)
            except ValidationError as exc:
                findings.extend(
                    _finding(
                        "OUTPUT_ROOT_BINDING_INVALID", str(error["msg"]), "$.binding"
                    )
                    for error in exc.errors(
                        include_url=False, include_input=False, include_context=False
                    )
                )
            else:
                binding_findings = validate_output_root_binding(
                    authorization=auth,
                    binding=binding,
                    output_dir=output_dir,
                    repository_root=repository_root,
                )
                findings.extend(binding_findings)
                output_root_authorized = not binding_findings

    normalize_targets = sorted(
        sheet.sheet_ordinal
        for sheet in auth.sheets
        if sheet.classification is SheetClassification.DATA_TABLE and sheet.normalize
    )
    if not normalize_targets:
        findings.append(
            _finding(
                "NO_NORMALIZE_TARGET_SHEET",
                "Normalize 대상 data_table Sheet가 최소 1개 필요하다",
                "$.authorization.sheets",
            )
        )
    if not auth.human_review_completed:
        findings.append(
            _finding(
                "HUMAN_REVIEW_INCOMPLETE",
                "human_review_completed=true 없이 Actual Normalize를 승인할 수 없다",
                "$.authorization.humanReviewCompleted",
            )
        )

    if findings:
        return _result(
            valid=False,
            authorized=[],
            sheet_coverage=sheet_coverage,
            finding_coverage=finding_coverage,
            identity_matched=identity_matched,
            output_root_authorized=output_root_authorized,
            blocking=blocking_count,
            reviewed=reviewed_count,
            human_review=auth.human_review_completed,
            findings=findings,
        )
    return _result(
        valid=True,
        authorized=normalize_targets,
        sheet_coverage=True,
        finding_coverage=True,
        identity_matched=True,
        output_root_authorized=output_root_authorized,
        blocking=0,
        reviewed=reviewed_count,
        human_review=True,
        findings=[],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate_normalization_authorization.py",
        description="Normalization Authorization Validator (ADR-0010)",
    )
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--output-root-binding", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--repository-root", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        report_bytes = args.report.read_bytes()
        report = json.loads(report_bytes.decode("utf-8"))
        authorization = json.loads(args.authorization.read_text(encoding="utf-8"))
        binding = (
            json.loads(args.output_root_binding.read_text(encoding="utf-8"))
            if args.output_root_binding is not None
            else None
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        print("[authz] valid=False (입력 파일을 읽을 수 없다)")
        return 1

    result = validate_authorization(
        inspection_report=report,
        inspection_report_bytes=report_bytes,
        authorization=authorization,
        output_root_binding=binding,
        output_dir=args.output_dir,
        repository_root=args.repository_root,
    )
    code_counts: dict[str, int] = {}
    findings_list = result.get("findings")
    findings_list = findings_list if isinstance(findings_list, list) else []
    for finding in findings_list:
        code = str(finding.get("code")) if isinstance(finding, dict) else "UNKNOWN"
        code_counts[code] = code_counts.get(code, 0) + 1
    print(
        "[authz] "
        f"valid={result['valid']} "
        f"authorizedSheetCount={len(result['authorizedSheetOrdinals'])} "  # type: ignore[arg-type]
        f"blockingFindingCount={result['blockingFindingCount']} "
        f"reviewedFindingCount={result['reviewedFindingCount']} "
        f"outputRootAuthorized={result['outputRootAuthorized']}"
    )
    for code in sorted(code_counts):
        print(f"[authz] finding {code}={code_counts[code]}")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
