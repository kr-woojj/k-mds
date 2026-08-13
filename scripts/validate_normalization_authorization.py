"""Normalization Authorization Validator (ADR-0010).

Inspection Report와 NormalizationAuthorization의 정합성을 결정론적으로
검증한다. Sheet 이름, Header 문자열, 실제 Path, Hash, 승인자 이름, 이메일,
Timestamp를 결과에 포함하지 않는다. 예외를 외부로 던지지 않는다.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from k_mds.models import (
    FindingDisposition,
    NormalizationAuthorization,
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
}


def _finding(code: str, message: str, path: str | None = None) -> dict[str, Any]:
    return {
        "severity": "ERROR",
        "code": code,
        "message": message,
        "path": path,
        "actualValue": None,
    }


def _result(
    *,
    valid: bool,
    authorized: list[int],
    blocking: int,
    reviewed: int,
    human_review: bool,
    findings: list[dict[str, Any]],
) -> dict[str, object]:
    return {
        "valid": valid,
        "classification": CLASSIFICATION,
        "authorizedSheetOrdinals": authorized,
        "blockingFindingCount": blocking,
        "reviewedFindingCount": reviewed,
        "humanReviewCompleted": human_review,
        "findings": findings,
    }


def _fail(
    findings: list[dict[str, Any]], *, blocking: int = 0, human_review: bool = False
) -> dict[str, object]:
    return _result(
        valid=False,
        authorized=[],
        blocking=blocking,
        reviewed=0,
        human_review=human_review,
        findings=findings,
    )


def _sheet_ordinal_from_path(path: object) -> int | None:
    if not isinstance(path, str):
        return None
    match = re.search(r"\$\.sheets\.(\d+)", path)
    return int(match.group(1)) if match else None


def validate_authorization(
    *,
    inspection_report: dict[str, object],
    authorization: dict[str, object],
) -> dict[str, object]:
    """Inspection Report와 Authorization의 정합성을 검증한다."""
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
                _finding(
                    "AUTHORIZATION_INVALID",
                    str(error["msg"]),
                    "$.authorization",
                )
                for error in exc.errors(
                    include_url=False, include_input=False, include_context=False
                )
            ]
        )

    findings: list[dict[str, Any]] = []
    if inspection_report.get("reportVersion") != SUPPORTED_REPORT_VERSION:
        findings.append(
            _finding(
                "REPORT_VERSION_UNSUPPORTED",
                "지원하지 않는 Inspection Report Version이다",
                "$.report.reportVersion",
            )
        )
        return _fail(findings, human_review=auth.human_review_completed)

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
                "REPORT_NOT_VERIFIED",
                "Inspection Report가 verified 상태가 아니다",
                "$.report",
            )
        )
        return _fail(findings, human_review=auth.human_review_completed)

    if inspection_report.get("sourceId") != auth.source_id:
        findings.append(
            _finding(
                "SOURCE_ID_MISMATCH",
                "Authorization sourceId가 Inspection Report와 일치하지 않는다",
                "$.authorization.sourceId",
            )
        )

    report_sheets = inspection_report.get("sheets")
    report_sheets = report_sheets if isinstance(report_sheets, list) else []
    for sheet in auth.sheets:
        if sheet.sheet_ordinal >= len(report_sheets):
            findings.append(
                _finding(
                    "SHEET_OUT_OF_RANGE",
                    f"승인된 sheetOrdinal {sheet.sheet_ordinal}이 Report 범위를 벗어난다",
                    f"$.authorization.sheets.{sheet.sheet_ordinal}",
                )
            )
            continue
        if sheet.classification is not SheetClassification.DATA_TABLE:
            continue
        report_sheet = report_sheets[sheet.sheet_ordinal]
        report_sheet = report_sheet if isinstance(report_sheet, dict) else {}
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

    # --- Finding 처분 검증 ---
    ack_by_key = {
        (item.code, item.sheet_ordinal): item for item in auth.acknowledged_findings
    }
    report_findings = inspection_report.get("findings")
    report_findings = report_findings if isinstance(report_findings, list) else []
    blocking_count = 0
    reviewed_count = 0
    for item in report_findings:
        if not isinstance(item, dict):
            findings.append(
                _finding("REPORT_NOT_OBJECT", "Inspection Finding이 Object가 아니다", "$.report")
            )
            continue
        code = str(item.get("code"))
        ordinal = _sheet_ordinal_from_path(item.get("path"))
        is_fatal = item.get("severity") == "ERROR"
        ack = ack_by_key.get((code, ordinal))

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
        if code in BLOCKING_CODES:
            if ack.disposition is not FindingDisposition.RESOLVED:
                blocking_count += 1
                findings.append(
                    _finding(
                        "BLOCKING_FINDING_UNRESOLVED",
                        "Blocking Finding은 resolved 처분만 승인할 수 있다",
                        "$.authorization.acknowledgedFindings",
                    )
                )
            continue
        if code in REVIEWABLE_CODES:
            if ack.disposition is FindingDisposition.REMAINS_BLOCKING:
                blocking_count += 1
                findings.append(
                    _finding(
                        "BLOCKING_FINDING_UNRESOLVED",
                        "remains_blocking 처분의 Finding이 남아 있다",
                        "$.authorization.acknowledgedFindings",
                    )
                )
            elif ack.disposition is FindingDisposition.ACCEPTED_FOR_REVIEWED_SCOPE:
                reviewed_count += 1
            continue
        # Unknown Finding은 명시적 Policy 추가 전 승인할 수 없다 (기본 blocking).
        blocking_count += 1
        findings.append(
            _finding(
                "UNKNOWN_FINDING_BLOCKING",
                "Policy에 정의되지 않은 Finding은 기본 blocking이다",
                "$.authorization.acknowledgedFindings",
            )
        )

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
        return _fail(
            findings,
            blocking=blocking_count,
            human_review=auth.human_review_completed,
        )
    return _result(
        valid=True,
        authorized=normalize_targets,
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
    args = parser.parse_args(argv)

    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        authorization = json.loads(args.authorization.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        print("[authz] valid=False (입력 파일을 읽을 수 없다)")
        return 1

    result = validate_authorization(
        inspection_report=report, authorization=authorization
    )
    print(
        "[authz] "
        f"valid={result['valid']} "
        f"authorizedSheetCount={len(result['authorizedSheetOrdinals'])} "  # type: ignore[arg-type]
        f"blockingFindingCount={result['blockingFindingCount']} "
        f"reviewedFindingCount={result['reviewedFindingCount']}"
    )
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
