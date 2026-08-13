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
