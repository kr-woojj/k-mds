"""Normalization Authorization Contract Test (ADR-0010 + Amendment).

실제 FAL50, Local Manifest, Actual Report, Actual Mapping에는 접근하지 않는다.
모든 Fixture는 TEST/FALTEST/urn:test 표기의 Synthetic 값만 사용한다.
Digest는 Synthetic Report Byte에서만 계산한다.
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

SYNTH_ID = "0" * 64


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
        exclusionReasonCode="TEST_EXCLUSION_001",
    )


def make_auth(**overrides: Any) -> dict[str, Any]:
    auth: dict[str, Any] = {
        "version": 1,
        "sourceId": "TEST-SOURCE-001",
        "inspectionReportId": SYNTH_ID,
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
        "reasonCode": "TEST_REASON_001",
    }


def report_to_bytes(report: dict[str, Any]) -> bytes:
    return json.dumps(report, ensure_ascii=False, sort_keys=True).encode("utf-8")


def run(
    report: Any,
    auth: Any,
    *,
    bind_identity: bool = True,
    report_bytes: bytes | None = None,
    **extra: Any,
) -> dict[str, Any]:
    data = (
        report_bytes
        if report_bytes is not None
        else (report_to_bytes(report) if isinstance(report, dict) else b"TEST-BYTES")
    )
    if bind_identity and isinstance(auth, dict):
        auth = {
            **auth,
            "inspectionReportId": validator_module.compute_inspection_report_id(data),
        }
    return validate_authorization(
        inspection_report=report,
        inspection_report_bytes=data,
        authorization=auth,
        **extra,
    )


def codes(result: dict[str, Any]) -> list[str]:
    return [finding["code"] for finding in result["findings"]]


# --- A. Report Identity ---


def test_matching_report_identity_succeeds() -> None:
    result = run(make_report(), make_auth())
    assert result["valid"] is True
    assert result["reportIdentityMatched"] is True


def test_identity_mismatch_fails() -> None:
    auth = make_auth(inspectionReportId="1" * 64)
    result = run(make_report(), auth, bind_identity=False)
    assert result["valid"] is False
    assert "INSPECTION_REPORT_ID_MISMATCH" in codes(result)


def test_short_identity_model_raises() -> None:
    with pytest.raises(ValidationError):
        NormalizationAuthorization.model_validate(make_auth(inspectionReportId="0" * 63))


def test_uppercase_identity_model_raises() -> None:
    with pytest.raises(ValidationError):
        NormalizationAuthorization.model_validate(make_auth(inspectionReportId="A" * 64))


def test_non_hex_identity_model_raises() -> None:
    with pytest.raises(ValidationError):
        NormalizationAuthorization.model_validate(make_auth(inspectionReportId="z" * 64))


def test_sha256_prefix_identity_model_raises() -> None:
    with pytest.raises(ValidationError):
        NormalizationAuthorization.model_validate(
            make_auth(inspectionReportId=f"sha256:{'0' * 57}")
        )


def test_same_dict_different_bytes_identity_mismatch() -> None:
    report = make_report()
    original = report_to_bytes(report)
    auth = make_auth(
        inspectionReportId=validator_module.compute_inspection_report_id(original)
    )
    reserialized = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
    result = run(report, auth, bind_identity=False, report_bytes=reserialized)
    assert result["valid"] is False
    assert "INSPECTION_REPORT_ID_MISMATCH" in codes(result)


def test_result_does_not_contain_digest() -> None:
    report = make_report()
    data = report_to_bytes(report)
    digest = validator_module.compute_inspection_report_id(data)
    result = run(report, make_auth())
    assert digest not in json.dumps(result, ensure_ascii=False, sort_keys=True)


# --- B. Sheet Coverage ---


def test_full_sheet_coverage_succeeds() -> None:
    result = run(make_report(), make_auth())
    assert result["sheetCoverageComplete"] is True
    assert result["authorizedSheetOrdinals"] == [0]


def test_missing_sheet_authorization_fails() -> None:
    auth = make_auth(sheets=[make_sheet(), make_excluded_sheet(1, "excluded_non_data")])
    result = run(make_report(), auth)
    assert result["valid"] is False
    assert "SHEET_AUTHORIZATION_MISSING" in codes(result)


def test_extra_sheet_authorization_fails() -> None:
    auth = make_auth(
        sheets=[
            make_sheet(),
            make_excluded_sheet(1, "excluded_non_data"),
            make_excluded_sheet(2, "metadata_or_readme"),
            make_excluded_sheet(7, "excluded_non_data"),
        ]
    )
    result = run(make_report(), auth)
    assert result["valid"] is False
    assert "SHEET_AUTHORIZATION_EXTRA" in codes(result)


def test_report_duplicate_sheet_ordinal_fails() -> None:
    report = make_report()
    report["sheets"].append(
        {"sheetOrdinal": 0, "inferredHeaderRow": 1, "headerConfidence": "high"}
    )
    result = run(report, make_auth())
    assert result["valid"] is False
    assert "REPORT_SHEET_ORDINAL_DUPLICATE" in codes(result)


def test_report_non_int_sheet_ordinal_fails() -> None:
    report = make_report()
    report["sheets"][0]["sheetOrdinal"] = "TEST"
    assert run(report, make_auth())["valid"] is False


def test_report_negative_sheet_ordinal_fails() -> None:
    report = make_report()
    report["sheets"][0]["sheetOrdinal"] = -1
    assert run(report, make_auth())["valid"] is False


def test_sheet_order_is_deterministically_sorted() -> None:
    auth = make_auth(
        sheets=[
            make_excluded_sheet(2, "metadata_or_readme"),
            make_sheet(
                sheetOrdinal=1, headerConfidence="medium", mediumConfidenceApproved=True
            ),
            make_sheet(sheetOrdinal=0),
        ]
    )
    result = run(make_report(), auth)
    assert result["valid"] is True
    assert result["authorizedSheetOrdinals"] == [0, 1]


def test_excluded_sheets_count_toward_coverage() -> None:
    result = run(make_report(), make_auth())
    assert result["sheetCoverageComplete"] is True


# --- C. Finding Exact Match와 정책 ---


def test_exact_finding_set_succeeds() -> None:
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
    assert result["findingCoverageComplete"] is True
    assert result["reviewedFindingCount"] == 1


def test_missing_finding_authorization_fails() -> None:
    report = make_report(
        findings=[make_finding("WORKBOOK_DECLARED_DIMENSION_EXCESSIVE")]
    )
    result = run(report, make_auth())
    assert result["valid"] is False
    assert "FINDING_AUTHORIZATION_MISSING" in codes(result)


def test_stale_finding_authorization_fails() -> None:
    auth = make_auth(
        acknowledgedFindings=[
            make_ack("WORKBOOK_PROTECTION_ENABLED", "accepted_for_reviewed_scope", None)
        ]
    )
    result = run(make_report(), auth)
    assert result["valid"] is False
    assert "FINDING_AUTHORIZATION_STALE" in codes(result)


def test_duplicate_report_finding_fails() -> None:
    report = make_report(
        findings=[
            make_finding("WORKBOOK_DECLARED_DIMENSION_EXCESSIVE"),
            make_finding("WORKBOOK_DECLARED_DIMENSION_EXCESSIVE"),
        ]
    )
    auth = make_auth(
        acknowledgedFindings=[
            make_ack(
                "WORKBOOK_DECLARED_DIMENSION_EXCESSIVE", "accepted_for_reviewed_scope"
            )
        ]
    )
    result = run(report, auth)
    assert result["valid"] is False
    assert "REPORT_FINDING_DUPLICATE" in codes(result)


def test_workbook_level_finding_matches_none_ordinal() -> None:
    report = make_report(findings=[make_finding("WORKBOOK_PROTECTION_ENABLED", None)])
    auth = make_auth(
        acknowledgedFindings=[
            make_ack("WORKBOOK_PROTECTION_ENABLED", "accepted_for_reviewed_scope", None)
        ]
    )
    assert run(report, auth)["valid"] is True


def test_ordinal_mismatch_yields_missing_and_stale() -> None:
    report = make_report(
        findings=[make_finding("WORKBOOK_DECLARED_DIMENSION_EXCESSIVE", 0)]
    )
    auth = make_auth(
        acknowledgedFindings=[
            make_ack(
                "WORKBOOK_DECLARED_DIMENSION_EXCESSIVE",
                "accepted_for_reviewed_scope",
                1,
            )
        ]
    )
    result = run(report, auth)
    assert result["valid"] is False
    assert "FINDING_AUTHORIZATION_MISSING" in codes(result)
    assert "FINDING_AUTHORIZATION_STALE" in codes(result)


def test_fatal_finding_cannot_be_authorized() -> None:
    fatal = make_finding("WORKBOOK_MACRO_DETECTED")
    fatal["severity"] = "ERROR"
    report = make_report(findings=[fatal])
    auth = make_auth(
        acknowledgedFindings=[make_ack("WORKBOOK_MACRO_DETECTED", "remains_blocking")]
    )
    result = run(report, auth)
    assert result["valid"] is False
    assert "FATAL_FINDING_PRESENT" in codes(result)


def test_current_blocking_resolved_still_fails() -> None:
    # 정책 변경(Amendment): 현재 Report의 Blocking Finding은 resolved로
    # 자기선언할 수 없다 — Inspector 재실행으로만 해소한다.
    report = make_report(findings=[make_finding("WORKBOOK_SCAN_LIMIT_REACHED")])
    auth = make_auth(
        acknowledgedFindings=[make_ack("WORKBOOK_SCAN_LIMIT_REACHED", "resolved")]
    )
    result = run(report, auth)
    assert result["valid"] is False
    assert "CURRENT_REPORT_BLOCKING_FINDING" in codes(result)


def test_current_blocking_accepted_scope_fails() -> None:
    report = make_report(findings=[make_finding("WORKBOOK_SCAN_LIMIT_REACHED")])
    auth = make_auth(
        acknowledgedFindings=[
            make_ack("WORKBOOK_SCAN_LIMIT_REACHED", "accepted_for_reviewed_scope")
        ]
    )
    result = run(report, auth)
    assert result["valid"] is False
    assert "CURRENT_REPORT_BLOCKING_FINDING" in codes(result)
    assert result["blockingFindingCount"] >= 1


def test_header_not_detected_is_current_blocking(tmp_path: Path) -> None:
    report = make_report(findings=[make_finding("WORKBOOK_HEADER_NOT_DETECTED", 2)])
    auth = make_auth(
        acknowledgedFindings=[make_ack("WORKBOOK_HEADER_NOT_DETECTED", "resolved", 2)]
    )
    assert run(report, auth)["valid"] is False


def test_reviewable_accepted_scope_succeeds() -> None:
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
    assert run(report, auth)["valid"] is True


def test_reviewable_remains_blocking_fails() -> None:
    report = make_report(
        findings=[make_finding("WORKBOOK_DECLARED_DIMENSION_EXCESSIVE")]
    )
    auth = make_auth(
        acknowledgedFindings=[
            make_ack("WORKBOOK_DECLARED_DIMENSION_EXCESSIVE", "remains_blocking")
        ]
    )
    assert run(report, auth)["valid"] is False


def test_unknown_finding_always_fails() -> None:
    report = make_report(findings=[make_finding("TEST-UNKNOWN-FINDING")])
    auth = make_auth(
        acknowledgedFindings=[make_ack("TEST-UNKNOWN-FINDING", "remains_blocking")]
    )
    result = run(report, auth)
    assert result["valid"] is False
    assert "UNKNOWN_FINDING_BLOCKING" in codes(result)


# --- D. Model Controlled Codes 및 기존 불변조건 ---


def _expect_model_error(auth: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        NormalizationAuthorization.model_validate(auth)


def test_valid_identity_and_reason_codes_accepted() -> None:
    auth = make_auth(
        acknowledgedFindings=[
            make_ack("WORKBOOK_PROTECTION_ENABLED", "accepted_for_reviewed_scope")
        ]
    )
    parsed = NormalizationAuthorization.model_validate(auth)
    assert parsed.inspection_report_id == SYNTH_ID
    assert parsed.acknowledged_findings[0].reason_code == "TEST_REASON_001"


def test_lowercase_reason_code_raises() -> None:
    ack = make_ack("WORKBOOK_PROTECTION_ENABLED", "accepted_for_reviewed_scope")
    ack["reasonCode"] = "test_reason_001"
    _expect_model_error(make_auth(acknowledgedFindings=[ack]))


def test_reason_code_with_path_separator_raises() -> None:
    ack = make_ack("WORKBOOK_PROTECTION_ENABLED", "accepted_for_reviewed_scope")
    ack["reasonCode"] = "TEST/REASON"
    _expect_model_error(make_auth(acknowledgedFindings=[ack]))


def test_invalid_exclusion_reason_code_raises() -> None:
    sheet = make_excluded_sheet(0, "metadata_or_readme")
    sheet["exclusionReasonCode"] = "test exclusion"
    _expect_model_error(make_auth(sheets=[sheet]))


def test_invalid_output_root_id_raises() -> None:
    _expect_model_error(make_auth(approvedOutputRootId="test-root"))


def test_duplicate_sheet_ordinal_raises() -> None:
    _expect_model_error(make_auth(sheets=[make_sheet(), make_sheet()]))


def test_data_table_invariants_still_enforced() -> None:
    _expect_model_error(make_auth(sheets=[make_sheet(normalize=False)]))
    _expect_model_error(make_auth(sheets=[make_sheet(headerRow=None)]))
    _expect_model_error(make_auth(sheets=[make_sheet(headerConfidence="low")]))
    _expect_model_error(make_auth(sheets=[make_sheet(headerConfidence="none")]))
    _expect_model_error(make_auth(sheets=[make_sheet(headerConfidence="medium")]))


def test_non_data_table_invariants_still_enforced() -> None:
    metadata = make_excluded_sheet(0, "metadata_or_readme")
    metadata["normalize"] = True
    _expect_model_error(make_auth(sheets=[metadata]))
    code_list = make_excluded_sheet(0, "code_list")
    code_list["normalize"] = True
    _expect_model_error(make_auth(sheets=[code_list]))
    missing_reason = make_excluded_sheet(0, "excluded_non_data")
    missing_reason["exclusionReasonCode"] = None
    _expect_model_error(make_auth(sheets=[missing_reason]))


def test_duplicate_finding_authorization_raises() -> None:
    _expect_model_error(
        make_auth(
            acknowledgedFindings=[
                make_ack("WORKBOOK_PROTECTION_ENABLED", "accepted_for_reviewed_scope"),
                make_ack("WORKBOOK_PROTECTION_ENABLED", "resolved"),
            ]
        )
    )


# --- Report 정합성 (기존 유지) ---


def test_source_id_mismatch_fails() -> None:
    result = run(make_report(sourceId="TEST-SOURCE-OTHER"), make_auth())
    assert result["valid"] is False
    assert "SOURCE_ID_MISMATCH" in codes(result)


def test_header_row_mismatch_fails() -> None:
    auth = make_auth(
        sheets=[
            make_sheet(headerRow=3),
            make_excluded_sheet(1, "excluded_non_data"),
            make_excluded_sheet(2, "metadata_or_readme"),
        ]
    )
    result = run(make_report(), auth)
    assert result["valid"] is False
    assert "HEADER_ROW_MISMATCH" in codes(result)


def test_header_confidence_mismatch_fails() -> None:
    auth = make_auth(
        sheets=[
            make_sheet(headerConfidence="medium", mediumConfidenceApproved=True),
            make_excluded_sheet(1, "excluded_non_data"),
            make_excluded_sheet(2, "metadata_or_readme"),
        ]
    )
    result = run(make_report(), auth)
    assert result["valid"] is False
    assert "HEADER_CONFIDENCE_MISMATCH" in codes(result)


def test_no_normalize_target_sheet_fails() -> None:
    auth = make_auth(
        sheets=[
            make_excluded_sheet(0, "metadata_or_readme"),
            make_excluded_sheet(1, "excluded_non_data"),
            make_excluded_sheet(2, "excluded_non_data"),
        ]
    )
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


# --- Empty Sheet Reviewable 정책 (ADR-0010 Amendment) ---


def make_empty_report(**overrides: Any) -> dict[str, Any]:
    report = make_report()
    report["sheets"].append(
        {"sheetOrdinal": 3, "inferredHeaderRow": None, "headerConfidence": "none"}
    )
    report["findings"].append(make_finding("WORKBOOK_EMPTY_SHEET", 3))
    report.update(overrides)
    return report


def make_empty_auth(classification: str = "excluded_non_data", **overrides: Any
                    ) -> dict[str, Any]:
    auth = make_auth()
    auth["sheets"].append(make_excluded_sheet(3, classification))
    auth["acknowledgedFindings"] = [
        make_ack("WORKBOOK_EMPTY_SHEET", "accepted_for_reviewed_scope", 3)
    ]
    auth.update(overrides)
    return auth


def test_empty_sheet_excluded_accepted_succeeds() -> None:
    result = run(make_empty_report(), make_empty_auth())
    assert result["valid"] is True
    assert result["reviewedFindingCount"] == 1
    assert result["authorizedSheetOrdinals"] == [0]
    assert result["sheetCoverageComplete"] is True
    assert result["findingCoverageComplete"] is True
    assert result["reportIdentityMatched"] is True


def test_empty_sheet_metadata_accepted_succeeds() -> None:
    result = run(make_empty_report(), make_empty_auth("metadata_or_readme"))
    assert result["valid"] is True


def test_empty_sheet_as_data_table_fails() -> None:
    auth = make_empty_auth()
    auth["sheets"][-1] = make_sheet(sheetOrdinal=3, headerRow=1, headerConfidence="high")
    result = run(make_empty_report(), auth)
    assert result["valid"] is False
    assert "EMPTY_SHEET_CLASSIFICATION_INVALID" in codes(result)


def test_empty_sheet_as_code_list_fails() -> None:
    auth = make_empty_auth()
    auth["sheets"][-1] = {
        "sheetOrdinal": 3,
        "classification": "code_list",
        "normalize": False,
        "headerRow": None,
        "headerConfidence": "none",
        "mediumConfidenceApproved": False,
        "exclusionReasonCode": None,
    }
    result = run(make_empty_report(), auth)
    assert result["valid"] is False
    assert "EMPTY_SHEET_CLASSIFICATION_INVALID" in codes(result)


def test_empty_sheet_authorization_missing_fails() -> None:
    auth = make_empty_auth(acknowledgedFindings=[])
    result = run(make_empty_report(), auth)
    assert result["valid"] is False
    assert "FINDING_AUTHORIZATION_MISSING" in codes(result)


def test_empty_sheet_stale_authorization_fails() -> None:
    auth = make_empty_auth()
    auth["acknowledgedFindings"].append(
        make_ack("WORKBOOK_EMPTY_SHEET", "accepted_for_reviewed_scope", 9)
    )
    result = run(make_empty_report(), auth)
    assert result["valid"] is False
    assert "FINDING_AUTHORIZATION_STALE" in codes(result)


@pytest.mark.parametrize("disposition", ["remains_blocking", "resolved"])
def test_empty_sheet_non_accepted_disposition_fails(disposition: str) -> None:
    auth = make_empty_auth()
    auth["acknowledgedFindings"][0]["disposition"] = disposition
    result = run(make_empty_report(), auth)
    assert result["valid"] is False
    assert "BLOCKING_FINDING_UNRESOLVED" in codes(result)


def test_only_empty_sheets_without_data_table_fails() -> None:
    report = make_empty_report()
    auth = make_empty_auth(
        sheets=[
            make_excluded_sheet(0, "excluded_non_data"),
            make_excluded_sheet(1, "excluded_non_data"),
            make_excluded_sheet(2, "metadata_or_readme"),
            make_excluded_sheet(3, "excluded_non_data"),
        ]
    )
    result = run(report, auth)
    assert result["valid"] is False
    assert "NO_NORMALIZE_TARGET_SHEET" in codes(result)


def test_empty_validator_result_deterministic() -> None:
    assert run(make_empty_report(), make_empty_auth()) == run(
        make_empty_report(), make_empty_auth()
    )


# --- Drawing-only Sheet Reviewable 정책 (ADR-0010 Amendment) ---


def make_drawing_only_report(**overrides: Any) -> dict[str, Any]:
    report = make_report()
    report["sheets"].append(
        {"sheetOrdinal": 3, "inferredHeaderRow": None, "headerConfidence": "none"}
    )
    report["findings"].append(make_finding("WORKBOOK_DRAWING_ONLY_SHEET", 3))
    report.update(overrides)
    return report


def make_drawing_only_auth(
    classification: str = "excluded_non_data", **overrides: Any
) -> dict[str, Any]:
    auth = make_auth()
    auth["sheets"].append(make_excluded_sheet(3, classification))
    auth["acknowledgedFindings"] = [
        make_ack("WORKBOOK_DRAWING_ONLY_SHEET", "accepted_for_reviewed_scope", 3)
    ]
    # ADR-0010 Amendment: Drawing-only Sheet는 완료된 Drawing Review 해소가
    # 있어야 metadata_or_readme 또는 excluded_non_data로 닫을 수 있다.
    auth["modelReferenceReviews"] = [
        {
            "sheetOrdinal": 3,
            "drawingReviewCategory": (
                "documentation"
                if classification == "metadata_or_readme"
                else "out_of_scope_visual"
            ),
            "completed": True,
            "referenceModelAlignmentApproved": False,
            "modelReferenceScopeApproved": False,
            "modelReferenceReviewerRecorded": False,
            "evidenceReferenceId": None,
            "externalVerificationAsserted": False,
            "externalVerificationTechnicallyConfirmed": False,
        }
    ]
    auth.update(overrides)
    return auth


def test_drawing_only_excluded_accepted_succeeds() -> None:
    result = run(make_drawing_only_report(), make_drawing_only_auth())
    assert result["valid"] is True
    assert result["reviewedFindingCount"] == 1
    assert result["authorizedSheetOrdinals"] == [0]
    assert result["reportIdentityMatched"] is True
    assert result["sheetCoverageComplete"] is True
    assert result["findingCoverageComplete"] is True


def test_drawing_only_metadata_accepted_succeeds() -> None:
    result = run(make_drawing_only_report(), make_drawing_only_auth("metadata_or_readme"))
    assert result["valid"] is True


def test_drawing_only_as_data_table_fails() -> None:
    auth = make_drawing_only_auth()
    auth["sheets"][-1] = make_sheet(sheetOrdinal=3, headerRow=1, headerConfidence="high")
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "DRAWING_ONLY_SHEET_CLASSIFICATION_INVALID" in codes(result)


def test_drawing_only_as_code_list_fails() -> None:
    auth = make_drawing_only_auth()
    auth["sheets"][-1] = {
        "sheetOrdinal": 3,
        "classification": "code_list",
        "normalize": False,
        "headerRow": None,
        "headerConfidence": "none",
        "mediumConfidenceApproved": False,
        "exclusionReasonCode": None,
    }
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "DRAWING_ONLY_SHEET_CLASSIFICATION_INVALID" in codes(result)


def test_drawing_only_authorization_missing_fails() -> None:
    result = run(make_drawing_only_report(), make_drawing_only_auth(acknowledgedFindings=[]))
    assert result["valid"] is False
    assert "FINDING_AUTHORIZATION_MISSING" in codes(result)


def test_drawing_only_stale_authorization_fails() -> None:
    auth = make_drawing_only_auth()
    auth["acknowledgedFindings"].append(
        make_ack("WORKBOOK_DRAWING_ONLY_SHEET", "accepted_for_reviewed_scope", 9)
    )
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "FINDING_AUTHORIZATION_STALE" in codes(result)


@pytest.mark.parametrize("disposition", ["remains_blocking", "resolved"])
def test_drawing_only_non_accepted_disposition_fails(disposition: str) -> None:
    auth = make_drawing_only_auth()
    auth["acknowledgedFindings"][0]["disposition"] = disposition
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "BLOCKING_FINDING_UNRESOLVED" in codes(result)


def test_only_drawing_only_without_data_table_fails() -> None:
    auth = make_drawing_only_auth(
        sheets=[
            make_excluded_sheet(0, "excluded_non_data"),
            make_excluded_sheet(1, "excluded_non_data"),
            make_excluded_sheet(2, "metadata_or_readme"),
            make_excluded_sheet(3, "excluded_non_data"),
        ]
    )
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "NO_NORMALIZE_TARGET_SHEET" in codes(result)


def test_drawing_only_validator_result_deterministic() -> None:
    assert run(make_drawing_only_report(), make_drawing_only_auth()) == run(
        make_drawing_only_report(), make_drawing_only_auth()
    )


# --- 비노출·결정론·Runtime Boundary ---


def test_result_has_no_disallowed_content() -> None:
    report = make_report(findings=[make_finding("WORKBOOK_SCAN_LIMIT_REACHED")])
    auth = make_auth(
        acknowledgedFindings=[make_ack("WORKBOOK_SCAN_LIMIT_REACHED", "resolved")]
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


def test_same_input_same_result_and_bytes() -> None:
    first = run(make_report(), make_auth())
    second = run(make_report(), make_auth())
    assert first == second
    assert json.dumps(first, sort_keys=True).encode("utf-8") == json.dumps(
        second, sort_keys=True
    ).encode("utf-8")


def test_non_bytes_report_input_fails() -> None:
    result = validate_authorization(
        inspection_report=make_report(),
        inspection_report_bytes="TEST-MARKER-BYTES",  # type: ignore[arg-type]
        authorization=make_auth(),
    )
    assert result["valid"] is False


def test_report_not_object_fails() -> None:
    result = run("TEST-MARKER-REPORT", make_auth(), bind_identity=True)
    assert result["valid"] is False


def test_authorization_not_object_fails() -> None:
    result = run(make_report(), "TEST-MARKER-AUTH", bind_identity=False)
    assert result["valid"] is False


def test_invalid_item_type_fails() -> None:
    result = run(make_report(), make_auth(sheets=[42]))
    assert result["valid"] is False
    assert "AUTHORIZATION_INVALID" in codes(result)


def test_extra_field_fails() -> None:
    assert run(make_report(), make_auth(unexpected_field="TEST"))["valid"] is False


def test_invalid_inputs_do_not_raise() -> None:
    bad_inputs: list[tuple[Any, Any]] = [
        (None, make_auth()),
        (make_report(), None),
        ([], {}),
        (make_report(), {"sheets": "TEST-MARKER"}),
    ]
    for report, auth in bad_inputs:
        result = run(report, auth, bind_identity=False)
        assert isinstance(result, dict)
        assert result["valid"] is False


def test_input_marker_not_exposed() -> None:
    result = run("TEST-MARKER-REPORT", "TEST-MARKER-AUTH", bind_identity=False)
    serialized = json.dumps(result, ensure_ascii=False, sort_keys=True)
    assert "TEST-MARKER" not in serialized
    assert "builtins." not in serialized


# --- Model Reference Authorization (ADR-0010 Amendment) ---
# 실제 IMO Compendium UML 내용, Class·Attribute·Association 이름, Drawing Target,
# Image 이름, 실제 Workbook File Name은 사용하지 않는다. Synthetic 값만 사용한다.


def make_model_reference_sheet(ordinal: int) -> dict[str, Any]:
    return make_sheet(
        sheetOrdinal=ordinal,
        classification="model_reference",
        normalize=False,
        headerRow=None,
        headerConfidence="none",
        exclusionReasonCode=None,
    )


def make_model_reference_review(ordinal: int = 3, **overrides: Any) -> dict[str, Any]:
    review: dict[str, Any] = {
        "sheetOrdinal": ordinal,
        "drawingReviewCategory": "imo_compendium_model_reference",
        "completed": True,
        "referenceModelAlignmentApproved": True,
        "modelReferenceScopeApproved": True,
        "modelReferenceReviewerRecorded": True,
        "evidenceReferenceId": "TEST-MODEL-REVIEW-EVIDENCE-001",
        "externalVerificationAsserted": True,
        "externalVerificationTechnicallyConfirmed": False,
    }
    review.update(overrides)
    return review


def make_model_reference_auth(**overrides: Any) -> dict[str, Any]:
    auth = make_auth()
    auth["sheets"].append(make_model_reference_sheet(3))
    auth["acknowledgedFindings"] = [
        make_ack("WORKBOOK_DRAWING_ONLY_SHEET", "accepted_for_reviewed_scope", 3)
    ]
    auth["modelReferenceReviews"] = [make_model_reference_review(3)]
    auth.update(overrides)
    return auth


# A. Model 불변조건


def test_model_reference_classification_model_validates() -> None:
    NormalizationAuthorization.model_validate(make_model_reference_auth())


def test_model_reference_normalize_true_raises() -> None:
    auth = make_model_reference_auth()
    auth["sheets"][-1]["normalize"] = True
    _expect_model_error(auth)


def test_model_reference_header_row_raises() -> None:
    auth = make_model_reference_auth()
    auth["sheets"][-1]["headerRow"] = 1
    _expect_model_error(auth)


@pytest.mark.parametrize("confidence", ["high", "medium", "low"])
def test_model_reference_non_none_confidence_raises(confidence: str) -> None:
    auth = make_model_reference_auth()
    auth["sheets"][-1]["headerConfidence"] = confidence
    _expect_model_error(auth)


def test_model_reference_medium_approved_raises() -> None:
    auth = make_model_reference_auth()
    auth["sheets"][-1]["mediumConfidenceApproved"] = True
    _expect_model_error(auth)


def test_model_reference_exclusion_reason_code_raises() -> None:
    auth = make_model_reference_auth()
    auth["sheets"][-1]["exclusionReasonCode"] = "TEST_EXCLUSION_001"
    _expect_model_error(auth)


def test_model_reference_review_invalid_evidence_id_raises() -> None:
    _expect_model_error(
        make_model_reference_auth(
            modelReferenceReviews=[
                make_model_reference_review(3, evidenceReferenceId="test lower id")
            ]
        )
    )


def test_model_reference_review_duplicate_ordinal_raises() -> None:
    _expect_model_error(
        make_model_reference_auth(
            modelReferenceReviews=[
                make_model_reference_review(3),
                make_model_reference_review(3),
            ]
        )
    )


def test_model_reference_review_extra_field_raises() -> None:
    _expect_model_error(
        make_model_reference_auth(
            modelReferenceReviews=[
                make_model_reference_review(3, unexpectedField="TEST")
            ]
        )
    )


# B. Authorization Validator Gate


def test_model_reference_full_gates_succeed() -> None:
    result = run(make_drawing_only_report(), make_model_reference_auth())
    assert result["valid"] is True
    # model_reference Sheet(3)는 authorizedSheetOrdinals에서 제외된다.
    assert result["authorizedSheetOrdinals"] == [0]
    assert result["sheetCoverageComplete"] is True
    assert result["findingCoverageComplete"] is True
    assert result["reportIdentityMatched"] is True
    assert result["reviewedFindingCount"] == 1


def test_model_reference_review_missing_fails() -> None:
    result = run(
        make_drawing_only_report(), make_model_reference_auth(modelReferenceReviews=[])
    )
    assert result["valid"] is False
    assert "MODEL_REFERENCE_REVIEW_REQUIRED" in codes(result)


def test_model_reference_review_not_completed_fails() -> None:
    auth = make_model_reference_auth(
        modelReferenceReviews=[make_model_reference_review(3, completed=False)]
    )
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "MODEL_REFERENCE_REVIEW_REQUIRED" in codes(result)


def test_reference_model_alignment_not_approved_fails() -> None:
    auth = make_model_reference_auth(
        modelReferenceReviews=[
            make_model_reference_review(3, referenceModelAlignmentApproved=False)
        ]
    )
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "REFERENCE_MODEL_ALIGNMENT_NOT_APPROVED" in codes(result)


def test_model_reference_scope_not_approved_fails() -> None:
    auth = make_model_reference_auth(
        modelReferenceReviews=[
            make_model_reference_review(3, modelReferenceScopeApproved=False)
        ]
    )
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "MODEL_REFERENCE_SCOPE_NOT_APPROVED" in codes(result)


def test_model_reference_reviewer_not_recorded_fails() -> None:
    auth = make_model_reference_auth(
        modelReferenceReviews=[
            make_model_reference_review(3, modelReferenceReviewerRecorded=False)
        ]
    )
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "MODEL_REFERENCE_REVIEWER_NOT_RECORDED" in codes(result)


def test_model_reference_evidence_reference_missing_fails() -> None:
    auth = make_model_reference_auth(
        modelReferenceReviews=[make_model_reference_review(3, evidenceReferenceId=None)]
    )
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "MODEL_REFERENCE_REVIEW_EVIDENCE_NOT_VERIFIED" in codes(result)


def test_model_reference_external_verification_not_asserted_fails() -> None:
    auth = make_model_reference_auth(
        modelReferenceReviews=[
            make_model_reference_review(3, externalVerificationAsserted=False)
        ]
    )
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "MODEL_REFERENCE_REVIEW_EVIDENCE_NOT_VERIFIED" in codes(result)


def test_model_reference_technical_confirmation_claim_fails() -> None:
    # Public Validator는 외부 Audit System Connector가 없으므로 기술적 확인을
    # 표현할 수 없다 — Assertion과 기술 검증을 분리한다.
    auth = make_model_reference_auth(
        modelReferenceReviews=[
            make_model_reference_review(
                3, externalVerificationTechnicallyConfirmed=True
            )
        ]
    )
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "MODEL_REFERENCE_REVIEW_EVIDENCE_NOT_VERIFIED" in codes(result)


@pytest.mark.parametrize(
    "category",
    [
        "documentation",
        "out_of_scope_visual",
        "separate_visual_review_required",
        "undecided",
    ],
)
def test_non_model_category_cannot_authorize_model_reference(category: str) -> None:
    auth = make_model_reference_auth(
        modelReferenceReviews=[
            make_model_reference_review(3, drawingReviewCategory=category)
        ]
    )
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "MODEL_REFERENCE_CLASSIFICATION_INVALID" in codes(result)


def test_model_reference_without_drawing_only_finding_fails() -> None:
    report = make_report()
    report["sheets"].append(
        {"sheetOrdinal": 3, "inferredHeaderRow": None, "headerConfidence": "none"}
    )
    auth = make_model_reference_auth(acknowledgedFindings=[])
    result = run(report, auth)
    assert result["valid"] is False
    assert "MODEL_REFERENCE_CLASSIFICATION_INVALID" in codes(result)


def test_model_reference_review_ordinal_mismatch_fails() -> None:
    auth = make_model_reference_auth(
        modelReferenceReviews=[make_model_reference_review(9)]
    )
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    result_codes = codes(result)
    assert "MODEL_REFERENCE_REVIEW_REQUIRED" in result_codes
    assert "MODEL_REFERENCE_CLASSIFICATION_INVALID" in result_codes


def test_model_reference_with_data_table_succeeds() -> None:
    result = run(make_drawing_only_report(), make_model_reference_auth())
    assert result["valid"] is True
    assert 0 in result["authorizedSheetOrdinals"]
    assert 3 not in result["authorizedSheetOrdinals"]


def test_model_reference_only_without_data_table_fails() -> None:
    auth = make_model_reference_auth(
        sheets=[
            make_excluded_sheet(0, "excluded_non_data"),
            make_excluded_sheet(1, "excluded_non_data"),
            make_excluded_sheet(2, "metadata_or_readme"),
            make_model_reference_sheet(3),
        ]
    )
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "NO_NORMALIZE_TARGET_SHEET" in codes(result)


def test_drawing_only_without_resolution_unresolved() -> None:
    # 단순 Drawing-only Sheet를 자동으로 model_reference 또는 excluded로
    # 닫을 수 없다 — 명시적 Drawing Review 해소가 필요하다.
    auth = make_drawing_only_auth()
    auth.pop("modelReferenceReviews", None)
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "MODEL_REFERENCE_AUTHORIZATION_CLASSIFICATION_UNRESOLVED" in codes(result)


def test_model_reference_downgrade_to_excluded_unresolved() -> None:
    # Model Reference로 확인된 Drawing을 excluded_non_data로 강등할 수 없다.
    auth = make_drawing_only_auth()
    auth["modelReferenceReviews"] = [make_model_reference_review(3)]
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "MODEL_REFERENCE_AUTHORIZATION_CLASSIFICATION_UNRESOLVED" in codes(result)


def test_resolution_category_pairing_mismatch_unresolved() -> None:
    # documentation 해소는 metadata_or_readme 분류와만 결합할 수 있다.
    auth = make_drawing_only_auth()
    auth["modelReferenceReviews"] = [
        make_model_reference_review(
            3,
            drawingReviewCategory="documentation",
            referenceModelAlignmentApproved=False,
            modelReferenceScopeApproved=False,
            modelReferenceReviewerRecorded=False,
            evidenceReferenceId=None,
            externalVerificationAsserted=False,
        )
    ]
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "MODEL_REFERENCE_AUTHORIZATION_CLASSIFICATION_UNRESOLVED" in codes(result)


def test_incomplete_resolution_unresolved() -> None:
    auth = make_drawing_only_auth()
    auth["modelReferenceReviews"] = [
        make_model_reference_review(
            3,
            drawingReviewCategory="out_of_scope_visual",
            completed=False,
            referenceModelAlignmentApproved=False,
            modelReferenceScopeApproved=False,
            modelReferenceReviewerRecorded=False,
            evidenceReferenceId=None,
            externalVerificationAsserted=False,
        )
    ]
    result = run(make_drawing_only_report(), auth)
    assert result["valid"] is False
    assert "MODEL_REFERENCE_AUTHORIZATION_CLASSIFICATION_UNRESOLVED" in codes(result)


def test_empty_sheet_needs_no_model_reference_resolution() -> None:
    # Empty Sheet는 Drawing Review 해소 대상이 아니다 (기존 Contract 유지).
    assert run(make_empty_report(), make_empty_auth())["valid"] is True


def test_model_reference_failure_findings_actual_value_null() -> None:
    failing_auths = [
        make_model_reference_auth(modelReferenceReviews=[]),
        make_model_reference_auth(
            modelReferenceReviews=[
                make_model_reference_review(
                    3,
                    completed=False,
                    referenceModelAlignmentApproved=False,
                    modelReferenceScopeApproved=False,
                    modelReferenceReviewerRecorded=False,
                    evidenceReferenceId=None,
                    externalVerificationAsserted=False,
                )
            ]
        ),
    ]
    for auth in failing_auths:
        result = run(make_drawing_only_report(), auth)
        assert result["valid"] is False
        assert result["findings"]
        for finding in result["findings"]:
            assert finding["actualValue"] is None


def test_model_reference_validator_deterministic() -> None:
    assert run(make_drawing_only_report(), make_model_reference_auth()) == run(
        make_drawing_only_report(), make_model_reference_auth()
    )


def test_model_reference_result_non_disclosure() -> None:
    for auth in (
        make_model_reference_auth(),
        make_model_reference_auth(modelReferenceReviews=[]),
    ):
        result = run(make_drawing_only_report(), auth)
        serialized = json.dumps(result, ensure_ascii=False, sort_keys=True)
        # Evidence ID·Workbook File Name·Sheet 이름·Digest·UML 내용은 결과에
        # 복사되지 않는다.
        assert "TEST-MODEL-REVIEW-EVIDENCE" not in serialized
        assert ".xlsx" not in serialized
        assert "TEST-SHEET" not in serialized
        assert "sha256" not in serialized.lower()
        for token in ("umlClass", "umlAttribute", "umlAssociation", "drawingTarget"):
            assert token not in serialized
