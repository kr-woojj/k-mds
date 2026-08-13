"""schema_validate Skill(Payload Validation) Contract Test (ADR-0002).

모든 Fixture는 TEST, FALTEST, urn:test 표기의 가상 값만 사용한다.
실제 IMO ID, Technical Position, KR Rule, KR GEARs Field를 사용하지 않는다.
"""

from typing import Any

from k_mds.models import ResultStatus, SkillResult
from k_mds.skills import schema_validate

VALID_PAYLOADS: dict[str, dict[str, Any]] = {
    "Dataset": {"dataset_id": "ds-test-1", "fal_version": "FALTEST", "name": "테스트 Dataset"},
    "DataElement": {"imo_id": "TEST-ELEMENT-001", "name": "테스트 데이터 요소"},
    "ElementOccurrence": {
        "occurrence_id": "occ-test-1",
        "dataset_id": "ds-test-1",
        "element_imo_id": "TEST-ELEMENT-001",
        "technical_position": "TEST/PATH/A",
    },
    "Evidence": {
        "evidenceId": "ev-test-001",
        "falVersion": "FALTEST",
        "ontologyVersion": "0.0.0-test",
        "profileVersion": "kr-ghg-0.0.0-test",
    },
    "ValidationFinding": {
        "severity": "ERROR",
        "code": "VAL_TEST_001",
        "message": "테스트용 가상 Finding이다.",
        "ruleId": "urn:test:rule:contract:0.0.1",
    },
    "SkillResult": {"status": "PASS", "humanReviewRequired": False},
}


# --- 유효 Payload PASS (지시 Test 1~6) ---


def test_valid_dataset_passes() -> None:
    assert schema_validate(VALID_PAYLOADS["Dataset"], "Dataset").status is ResultStatus.PASS


def test_valid_data_element_passes() -> None:
    assert schema_validate(VALID_PAYLOADS["DataElement"], "DataElement").status is ResultStatus.PASS


def test_valid_element_occurrence_passes() -> None:
    result = schema_validate(VALID_PAYLOADS["ElementOccurrence"], "ElementOccurrence")
    assert result.status is ResultStatus.PASS


def test_valid_evidence_passes() -> None:
    assert schema_validate(VALID_PAYLOADS["Evidence"], "Evidence").status is ResultStatus.PASS


def test_valid_validation_finding_passes() -> None:
    result = schema_validate(VALID_PAYLOADS["ValidationFinding"], "ValidationFinding")
    assert result.status is ResultStatus.PASS


def test_valid_skill_result_payload_passes() -> None:
    # 바깥쪽 SkillResult는 Skill 실행 Contract이고, 검증 대상 Payload는
    # normalizedPayload에 들어간다 (지시 8항).
    result = schema_validate(VALID_PAYLOADS["SkillResult"], "SkillResult")
    assert result.status is ResultStatus.PASS
    assert result.data["normalizedPayload"]["status"] == "PASS"
    assert result.data["normalizedPayload"]["humanReviewRequired"] is False


# --- 유효하지 않은 Payload FAIL (지시 Test 7~13) ---


def test_dataset_missing_required_field_fails() -> None:
    payload: dict[str, object] = {"dataset_id": "ds-test-1"}
    assert schema_validate(payload, "Dataset").status is ResultStatus.FAIL


def test_data_element_with_empty_imo_id_fails() -> None:
    payload: dict[str, object] = {"imo_id": "", "name": "테스트 데이터 요소"}
    assert schema_validate(payload, "DataElement").status is ResultStatus.FAIL


def test_occurrence_without_element_reference_fails() -> None:
    payload: dict[str, object] = {"occurrence_id": "occ-test-1", "dataset_id": "ds-test-1"}
    assert schema_validate(payload, "ElementOccurrence").status is ResultStatus.FAIL


def test_occurrence_approved_without_position_fails() -> None:
    payload: dict[str, object] = {
        "occurrence_id": "occ-test-1",
        "dataset_id": "ds-test-1",
        "element_imo_id": "TEST-ELEMENT-001",
        "status": "approved",
    }
    assert schema_validate(payload, "ElementOccurrence").status is ResultStatus.FAIL


def test_skill_result_pass_with_errors_fails() -> None:
    payload = {
        "status": "PASS",
        "humanReviewRequired": False,
        "errors": [dict(VALID_PAYLOADS["ValidationFinding"])],
    }
    assert schema_validate(payload, "SkillResult").status is ResultStatus.FAIL


def test_skill_result_warning_without_warnings_fails() -> None:
    payload = {"status": "WARNING", "humanReviewRequired": True}
    assert schema_validate(payload, "SkillResult").status is ResultStatus.FAIL


def test_skill_result_fail_without_errors_fails() -> None:
    payload = {"status": "FAIL", "humanReviewRequired": True}
    assert schema_validate(payload, "SkillResult").status is ResultStatus.FAIL


# --- 입력 경계 (지시 Test 14~15) ---


def test_unsupported_model_name_fails() -> None:
    assert schema_validate({}, "UnknownModel").status is ResultStatus.FAIL


def test_non_dict_payload_fails() -> None:
    result = schema_validate("not-a-dict", "Dataset")  # type: ignore[arg-type]
    assert result.status is ResultStatus.FAIL


# --- Runtime 입력 경계: model_name 타입 (예외 비전파) ---

INVALID_NAME_INPUTS: list[object] = [
    None,
    ["TEST-MARKER-LIST"],
    {"key": "TEST-MARKER-DICT"},
    42,
]


def _invalid_name_results() -> list[SkillResult]:
    return [
        schema_validate(VALID_PAYLOADS["Dataset"], item)  # type: ignore[arg-type]
        for item in INVALID_NAME_INPUTS
    ]


def test_model_name_none_fails() -> None:
    result = schema_validate(VALID_PAYLOADS["Dataset"], None)  # type: ignore[arg-type]
    assert result.status is ResultStatus.FAIL


def test_model_name_list_fails() -> None:
    result = schema_validate(VALID_PAYLOADS["Dataset"], [])  # type: ignore[arg-type]
    assert result.status is ResultStatus.FAIL


def test_model_name_dict_fails() -> None:
    result = schema_validate(VALID_PAYLOADS["Dataset"], {})  # type: ignore[arg-type]
    assert result.status is ResultStatus.FAIL


def test_model_name_int_fails() -> None:
    result = schema_validate(VALID_PAYLOADS["Dataset"], 42)  # type: ignore[arg-type]
    assert result.status is ResultStatus.FAIL


def test_invalid_model_name_type_does_not_raise() -> None:
    for item in INVALID_NAME_INPUTS:
        result = schema_validate(VALID_PAYLOADS["Dataset"], item)  # type: ignore[arg-type]
        assert isinstance(result, SkillResult)


def test_invalid_model_name_results_satisfy_fail_contract() -> None:
    for result in _invalid_name_results():
        assert result.status is ResultStatus.FAIL
        assert result.human_review_required is True
        assert len(result.errors) >= 1
        assert result.evidence == []


def test_invalid_model_name_first_finding_contract() -> None:
    for result in _invalid_name_results():
        finding = result.errors[0]
        assert finding.code == "MODEL_NAME_NOT_STRING"
        assert finding.path == "$.modelName"
        assert finding.actual_value is None


def test_invalid_model_name_marker_not_exposed() -> None:
    for result in _invalid_name_results():
        dumped = result.model_dump_json(by_alias=True)
        assert "TEST-MARKER-LIST" not in dumped
        assert "TEST-MARKER-DICT" not in dumped
        assert "builtins." not in dumped


def test_supported_model_still_passes() -> None:
    assert schema_validate(VALID_PAYLOADS["Dataset"], "Dataset").status is ResultStatus.PASS


def test_unsupported_string_model_keeps_existing_code() -> None:
    result = schema_validate({}, "UnknownModel")
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "UNSUPPORTED_MODEL_NAME"


# --- 불변조건 (지시 Test 16~17) ---


def _fail_results() -> list[SkillResult]:
    return [
        schema_validate({}, "Dataset"),
        schema_validate({"imo_id": ""}, "DataElement"),
        schema_validate({}, "UnknownModel"),
        schema_validate("not-a-dict", "Dataset"),  # type: ignore[arg-type]
    ]


def test_all_fail_results_require_human_review() -> None:
    for result in _fail_results():
        assert result.status is ResultStatus.FAIL
        assert result.human_review_required is True
        assert len(result.errors) >= 1


def test_all_pass_results_have_no_findings() -> None:
    for model_name, payload in VALID_PAYLOADS.items():
        result = schema_validate(payload, model_name)
        assert result.status is ResultStatus.PASS, model_name
        assert result.human_review_required is False
        assert result.errors == [] and result.warnings == []


# --- normalizedPayload alias 정책 (지시 Test 18) ---


def test_normalized_payload_follows_alias_policy() -> None:
    evidence = schema_validate(VALID_PAYLOADS["Evidence"], "Evidence").data["normalizedPayload"]
    assert "evidenceId" in evidence and "evidence_id" not in evidence

    skill = schema_validate(VALID_PAYLOADS["SkillResult"], "SkillResult").data["normalizedPayload"]
    assert "humanReviewRequired" in skill and "human_review_required" not in skill

    dataset = schema_validate(VALID_PAYLOADS["Dataset"], "Dataset").data["normalizedPayload"]
    assert "dataset_id" in dataset and "datasetId" not in dataset


# --- 원본 값 비노출 (지시 Test 19~20) ---


def test_findings_do_not_expose_input_values() -> None:
    marker = "TEST-DO-NOT-LEAK-001"
    result = schema_validate({"imo_id": marker}, "DataElement")  # name 누락으로 FAIL
    assert result.status is ResultStatus.FAIL
    assert marker not in result.model_dump_json(by_alias=True)


def test_finding_actual_value_is_always_none() -> None:
    for result in _fail_results():
        for finding in result.errors:
            assert finding.actual_value is None


# --- Skill 실행 Contract (지시 Test 21~22) ---


def test_returns_skill_result_instance() -> None:
    assert isinstance(schema_validate(VALID_PAYLOADS["Dataset"], "Dataset"), SkillResult)


def test_result_serializes_with_camel_case_alias() -> None:
    dumped = schema_validate(VALID_PAYLOADS["Dataset"], "Dataset").model_dump(by_alias=True)
    assert "humanReviewRequired" in dumped
    assert "human_review_required" not in dumped
