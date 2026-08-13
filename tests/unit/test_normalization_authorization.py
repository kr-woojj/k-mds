"""Normalization Authorization Contract Test (ADR-0010).

실제 FAL50, Local Manifest, Actual Report, Actual Mapping에는 접근하지 않는다.
모든 Fixture는 TEST/FALTEST/urn:test 표기의 Synthetic 값만 사용한다.
"""

import json
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from k_mds.models import NormalizationAuthorization

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_normalization_authorization as validator_module  # noqa: E402

validate_authorization = validator_module.validate_authorization


def make_report(**overrides: Any) -> dict[str, Any]:
    report: dict[str, Any] = {
        "reportVersion": 1,
        "provenanceVerified": True,
        "manifestStatus": "verified",
        "inspectionMode": "verified-source",
        "sourceId": "TEST-SOURCE-001",
        "sheets": [
            {"sheetOrdinal": 0, "inferredHeaderRow": 1, "headerConfidence": "high"},
            {"sheetOrdinal": 1, "inferredHeaderRow": 1, "headerConfidence": "medium"},
            {"sheetOrdinal": 2, "inferredHeaderRow": None, "headerConfidence": "none"},
        ],
        "findings": [],
        "summary": {
            "inspectionCompleted": True,
            "normalizationReady": False,
            "humanReviewRequired": True,
        },
    }
    report.update(overrides)
    return report


def make_sheet(**overrides: Any) -> dict[str, Any]:
    sheet: dict[str, Any] = {
        "sheetOrdinal": 0,
        "classification": "data_table",
        "normalize": True,
        "headerRow": 1,
        "headerConfidence": "high",
        "mediumConfidenceApproved": False,
        "exclusionReasonCode": None,
    }
    sheet.update(overrides)
    return sheet


def make_excluded_sheet(ordinal: int, classification: str) -> dict[str, Any]:
    return make_sheet(
        sheetOrdinal=ordinal,
        classification=classification,
        normalize=False,
        headerRow=None,
        headerConfidence="none",
        exclusionReasonCode="TEST-EXCLUSION-001",
    )


def make_auth(**overrides: Any) -> dict[str, Any]:
    auth: dict[str, Any] = {
        "version": 1,
        "sourceId": "TEST-SOURCE-001",
        "inspectionReportId": "TEST-INSPECTION-001",
        "outputStorageClass": "internal-restricted",
        "approvedOutputRootId": "TEST-RESTRICTED-ROOT-001",
        "sheets": [
            make_sheet(),
            make_excluded_sheet(1, "excluded_non_data"),
            make_excluded_sheet(2, "metadata_or_readme"),
        ],
        "acknowledgedFindings": [],
        "humanReviewCompleted": True,
    }
    auth.update(overrides)
    return auth


def make_finding(code: str, sheet_ordinal: int | None = 0) -> dict[str, Any]:
    path = f"$.sheets.{sheet_ordinal}" if sheet_ordinal is not None else "$.workbook"
    return {
        "severity": "WARNING",
        "code": code,
        "message": "TEST",
        "path": path,
        "actualValue": None,
    }


def make_ack(
    code: str,
    disposition: str,
    sheet_ordinal: int | None = 0,
) -> dict[str, Any]:
    return {
        "code": code,
        "sheetOrdinal": sheet_ordinal,
        "disposition": disposition,
        "reasonCode": "TEST-REASON-001",
    }


def run(report: dict[str, Any], auth: dict[str, Any]) -> dict[str, Any]:
    return validate_authorization(inspection_report=report, authorization=auth)


def codes(result: dict[str, Any]) -> list[str]:
    return [finding["code"] for finding in result["findings"]]


# --- A. 유효 상태 ---


def test_high_confidence_data_table_authorized() -> None:
    result = run(make_report(), make_auth())
    assert result["valid"] is True
    assert result["authorizedSheetOrdinals"] == [0]
    assert result["classification"] == "internal-restricted"


def test_medium_confidence_with_explicit_approval() -> None:
    auth = make_auth(
        sheets=[
            make_sheet(),
            make_sheet(
                sheetOrdinal=1,
                headerConfidence="medium",
                mediumConfidenceApproved=True,
            ),
            make_excluded_sheet(2, "metadata_or_readme"),
        ]
    )
    result = run(make_report(), auth)
    assert result["valid"] is True
    assert result["authorizedSheetOrdinals"] == [0, 1]


def test_metadata_and_excluded_sheets_accepted() -> None:
    result = run(make_report(), make_auth())
    assert result["valid"] is True


def test_multiple_sheet_order_is_deterministic() -> None:
    auth = make_auth(
        sheets=[
            make_sheet(
                sheetOrdinal=1, headerConfidence="medium", mediumConfidenceApproved=True
            ),
            make_sheet(sheetOrdinal=0),
            make_excluded_sheet(2, "metadata_or_readme"),
        ]
    )
    result = run(make_report(), auth)
    assert result["authorizedSheetOrdinals"] == [0, 1]


def test_same_input_same_result() -> None:
    assert run(make_report(), make_auth()) == run(make_report(), make_auth())


# --- B. Sheet 불변조건 (Model) ---


def _expect_model_error(auth: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        NormalizationAuthorization.model_validate(auth)


def test_duplicate_sheet_ordinal_raises() -> None:
    _expect_model_error(make_auth(sheets=[make_sheet(), make_sheet()]))


def test_data_table_without_normalize_raises() -> None:
    _expect_model_error(make_auth(sheets=[make_sheet(normalize=False)]))


def test_data_table_without_header_row_raises() -> None:
    _expect_model_error(make_auth(sheets=[make_sheet(headerRow=None)]))


def test_data_table_low_confidence_raises() -> None:
    _expect_model_error(make_auth(sheets=[make_sheet(headerConfidence="low")]))


def test_data_table_none_confidence_raises() -> None:
    _expect_model_error(make_auth(sheets=[make_sheet(headerConfidence="none")]))


def test_medium_without_approval_raises() -> None:
    _expect_model_error(make_auth(sheets=[make_sheet(headerConfidence="medium")]))


def test_metadata_with_normalize_raises() -> None:
    sheet = make_excluded_sheet(0, "metadata_or_readme")
    sheet["normalize"] = True
    _expect_model_error(make_auth(sheets=[sheet]))


def test_metadata_without_reason_raises() -> None:
    sheet = make_excluded_sheet(0, "metadata_or_readme")
    sheet["exclusionReasonCode"] = None
    _expect_model_error(make_auth(sheets=[sheet]))


def test_excluded_with_normalize_raises() -> None:
    sheet = make_excluded_sheet(0, "excluded_non_data")
    sheet["normalize"] = True
    _expect_model_error(make_auth(sheets=[sheet]))


def test_excluded_without_reason_raises() -> None:
    sheet = make_excluded_sheet(0, "excluded_non_data")
    sheet["exclusionReasonCode"] = None
    _expect_model_error(make_auth(sheets=[sheet]))


def test_code_list_with_normalize_raises() -> None:
    sheet = make_excluded_sheet(0, "code_list")
    sheet["normalize"] = True
    _expect_model_error(make_auth(sheets=[sheet]))


def test_output_root_id_with_path_separator_raises() -> None:
    _expect_model_error(make_auth(approvedOutputRootId="TEST/ROOT"))


# --- C. Finding 처리 ---


def test_scan_limit_remains_blocking_fails() -> None:
    report = make_report(findings=[make_finding("WORKBOOK_SCAN_LIMIT_REACHED")])
    auth = make_auth(
        acknowledgedFindings=[make_ack("WORKBOOK_SCAN_LIMIT_REACHED", "remains_blocking")]
    )
    result = run(report, auth)
    assert result["valid"] is False
    assert result["blockingFindingCount"] >= 1


def test_scan_limit_accepted_scope_fails() -> None:
    report = make_report(findings=[make_finding("WORKBOOK_SCAN_LIMIT_REACHED")])
    auth = make_auth(
        acknowledgedFindings=[
            make_ack("WORKBOOK_SCAN_LIMIT_REACHED", "accepted_for_reviewed_scope")
        ]
    )
    result = run(report, auth)
    assert result["valid"] is False
    assert "BLOCKING_FINDING_UNRESOLVED" in codes(result)


def test_scan_limit_resolved_succeeds() -> None:
    report = make_report(findings=[make_finding("WORKBOOK_SCAN_LIMIT_REACHED")])
    auth = make_auth(
        acknowledgedFindings=[make_ack("WORKBOOK_SCAN_LIMIT_REACHED", "resolved")]
    )
    assert run(report, auth)["valid"] is True


def test_header_not_detected_data_table_fails() -> None:
    report = make_report(findings=[make_finding("WORKBOOK_HEADER_NOT_DETECTED", 2)])
    auth = make_auth(
        sheets=[
            make_sheet(),
            make_excluded_sheet(1, "excluded_non_data"),
            make_sheet(sheetOrdinal=2),
        ],
        acknowledgedFindings=[
            make_ack("WORKBOOK_HEADER_NOT_DETECTED", "remains_blocking", 2)
        ],
    )
    assert run(report, auth)["valid"] is False


def test_xml_skip_unresolved_fails() -> None:
    report = make_report(
        findings=[make_finding("WORKBOOK_XML_PART_SCAN_SKIPPED", None)]
    )
    auth = make_auth(
        acknowledgedFindings=[
            make_ack("WORKBOOK_XML_PART_SCAN_SKIPPED", "accepted_for_reviewed_scope", None)
        ]
    )
    assert run(report, auth)["valid"] is False


def test_fatal_error_finding_fails() -> None:
    fatal = make_finding("WORKBOOK_MACRO_DETECTED")
    fatal["severity"] = "ERROR"
    report = make_report(findings=[fatal])
    auth = make_auth(
        acknowledgedFindings=[make_ack("WORKBOOK_MACRO_DETECTED", "remains_blocking")]
    )
    result = run(report, auth)
    assert result["valid"] is False
    assert "FATAL_FINDING_PRESENT" in codes(result)


def test_declared_dimension_reviewed_scope_succeeds() -> None:
    report = make_report(
        findings=[make_finding("WORKBOOK_DECLARED_DIMENSION_EXCESSIVE")]
    )
    auth = make_auth(
        acknowledgedFindings=[
            make_ack(
                "WORKBOOK_DECLARED_DIMENSION_EXCESSIVE", "accepted_for_reviewed_scope"
            )
        ]
    )
    result = run(report, auth)
    assert result["valid"] is True
    assert result["reviewedFindingCount"] == 1


def test_protection_reviewed_scope_succeeds() -> None:
    report = make_report(
        findings=[make_finding("WORKBOOK_PROTECTION_ENABLED", None)]
    )
    auth = make_auth(
        acknowledgedFindings=[
            make_ack("WORKBOOK_PROTECTION_ENABLED", "accepted_for_reviewed_scope", None)
        ]
    )
    assert run(report, auth)["valid"] is True


def test_unknown_finding_is_blocking() -> None:
    report = make_report(findings=[make_finding("TEST-UNKNOWN-FINDING")])
    auth = make_auth(
        acknowledgedFindings=[make_ack("TEST-UNKNOWN-FINDING", "remains_blocking")]
    )
    result = run(report, auth)
    assert result["valid"] is False
    assert "UNKNOWN_FINDING_BLOCKING" in codes(result)


def test_missing_finding_authorization_fails() -> None:
    report = make_report(
        findings=[make_finding("WORKBOOK_DECLARED_DIMENSION_EXCESSIVE")]
    )
    result = run(report, make_auth())
    assert result["valid"] is False
    assert "FINDING_AUTHORIZATION_MISSING" in codes(result)


def test_duplicate_finding_authorization_raises() -> None:
    _expect_model_error(
        make_auth(
            acknowledgedFindings=[
                make_ack("WORKBOOK_PROTECTION_ENABLED", "accepted_for_reviewed_scope"),
                make_ack("WORKBOOK_PROTECTION_ENABLED", "resolved"),
            ]
        )
    )


# --- D. Report 정합성 ---


def test_source_id_mismatch_fails() -> None:
    result = run(make_report(sourceId="TEST-SOURCE-OTHER"), make_auth())
    assert result["valid"] is False
    assert "SOURCE_ID_MISMATCH" in codes(result)


def test_sheet_out_of_range_fails() -> None:
    auth = make_auth(sheets=[make_sheet(sheetOrdinal=7)])
    result = run(make_report(), auth)
    assert result["valid"] is False
    assert "SHEET_OUT_OF_RANGE" in codes(result)


def test_header_row_mismatch_fails() -> None:
    auth = make_auth(sheets=[make_sheet(headerRow=3)])
    result = run(make_report(), auth)
    assert result["valid"] is False
    assert "HEADER_ROW_MISMATCH" in codes(result)


def test_header_confidence_mismatch_fails() -> None:
    auth = make_auth(
        sheets=[make_sheet(headerConfidence="medium", mediumConfidenceApproved=True)]
    )
    result = run(make_report(), auth)
    assert result["valid"] is False
    assert "HEADER_CONFIDENCE_MISMATCH" in codes(result)


def test_no_normalize_target_sheet_fails() -> None:
    auth = make_auth(sheets=[make_excluded_sheet(0, "metadata_or_readme")])
    result = run(make_report(), auth)
    assert result["valid"] is False
    assert "NO_NORMALIZE_TARGET_SHEET" in codes(result)


def test_human_review_incomplete_fails() -> None:
    result = run(make_report(), make_auth(humanReviewCompleted=False))
    assert result["valid"] is False
    assert "HUMAN_REVIEW_INCOMPLETE" in codes(result)


def test_unsupported_report_version_fails() -> None:
    result = run(make_report(reportVersion=99), make_auth())
    assert result["valid"] is False
    assert "REPORT_VERSION_UNSUPPORTED" in codes(result)


def test_unverified_report_fails() -> None:
    result = run(make_report(provenanceVerified=False), make_auth())
    assert result["valid"] is False
    assert "REPORT_NOT_VERIFIED" in codes(result)


def test_incomplete_inspection_fails() -> None:
    report = make_report()
    report["summary"]["inspectionCompleted"] = False
    result = run(report, make_auth())
    assert result["valid"] is False


# --- E. 비노출과 결정론 ---


def test_result_has_no_disallowed_content() -> None:
    report = make_report(findings=[make_finding("WORKBOOK_SCAN_LIMIT_REACHED")])
    auth = make_auth(
        acknowledgedFindings=[make_ack("WORKBOOK_SCAN_LIMIT_REACHED", "remains_blocking")]
    )
    for result in (run(make_report(), make_auth()), run(report, auth)):
        serialized = json.dumps(result, ensure_ascii=False, sort_keys=True)
        assert "TEST-SHEET" not in serialized
        assert "TEST-HEADER" not in serialized
        assert "c:\\" not in serialized.lower() and "c:/" not in serialized.lower()
        assert "sha256" not in serialized.lower()
        assert "generatedAt" not in serialized and "timestamp" not in serialized
        for finding in result["findings"]:
            assert finding["actualValue"] is None


def test_same_input_same_serialized_bytes() -> None:
    first = json.dumps(run(make_report(), make_auth()), sort_keys=True).encode("utf-8")
    second = json.dumps(run(make_report(), make_auth()), sort_keys=True).encode("utf-8")
    assert first == second


# --- F. Runtime Boundary ---


def test_report_not_object_fails() -> None:
    result = validate_authorization(
        inspection_report="TEST-MARKER-REPORT",  # type: ignore[arg-type]
        authorization=make_auth(),
    )
    assert result["valid"] is False


def test_authorization_not_object_fails() -> None:
    result = validate_authorization(
        inspection_report=make_report(),
        authorization="TEST-MARKER-AUTH",  # type: ignore[arg-type]
    )
    assert result["valid"] is False


def test_invalid_item_type_fails() -> None:
    result = run(make_report(), make_auth(sheets=[42]))
    assert result["valid"] is False
    assert "AUTHORIZATION_INVALID" in codes(result)


def test_extra_field_fails() -> None:
    result = run(make_report(), make_auth(unexpected_field="TEST"))
    assert result["valid"] is False


def test_invalid_inputs_do_not_raise() -> None:
    bad_inputs: list[tuple[Any, Any]] = [
        (None, make_auth()),
        (make_report(), None),
        ([], {}),
        (make_report(), {"sheets": "TEST-MARKER"}),
    ]
    for report, auth in bad_inputs:
        result = validate_authorization(inspection_report=report, authorization=auth)
        assert isinstance(result, dict)
        assert result["valid"] is False


def test_input_marker_not_exposed() -> None:
    result = validate_authorization(
        inspection_report="TEST-MARKER-REPORT",  # type: ignore[arg-type]
        authorization="TEST-MARKER-AUTH",  # type: ignore[arg-type]
    )
    serialized = json.dumps(result, ensure_ascii=False, sort_keys=True)
    assert "TEST-MARKER" not in serialized
    assert "builtins." not in serialized
