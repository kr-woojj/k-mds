"""schema_contract_check Skill Contract Test (ADR-0002).

generated Schema artifact의 구조 무결성 검사를 검증한다.
Fixture schema는 전부 테스트 내부에서 합성한 가상 구조다.
"""

import json
from pathlib import Path
from typing import Any

from k_mds.models import ResultStatus, SkillResult
from k_mds.skills import schema_contract_check


def write_schema(directory: Path, name: str, schema: dict[str, Any]) -> None:
    (directory / f"{name}.schema.json").write_text(
        json.dumps(schema, ensure_ascii=False), encoding="utf-8"
    )


def valid_validation_schema() -> dict[str, Any]:
    return {"$defs": {"SkillResult": {"properties": {"humanReviewRequired": {}}}}}


def valid_ontology_schema() -> dict[str, Any]:
    return {
        "$defs": {
            "DataElement": {"properties": {}},
            "ElementOccurrence": {"properties": {"element_imo_id": {}}},
        }
    }


# --- PASS 경로 ---


def test_validation_artifact_returns_pass() -> None:
    assert schema_contract_check("validation").status is ResultStatus.PASS


def test_ontology_artifact_returns_pass() -> None:
    assert schema_contract_check("ontology").status is ResultStatus.PASS


def test_pass_data_contains_validation_level() -> None:
    data = schema_contract_check("validation").data
    assert data["schemaName"] == "validation"
    assert data["validationLevel"] == "contract-structure"
    assert data["checkedDefinitions"] == ["SkillResult"]


# --- FAIL 경로 ---


def test_unsupported_schema_name_returns_fail() -> None:
    assert schema_contract_check("unknown-schema").status is ResultStatus.FAIL


def test_missing_schema_file_returns_fail(tmp_path: Path) -> None:
    assert schema_contract_check("validation", schema_dir=tmp_path).status is ResultStatus.FAIL


def test_broken_json_schema_returns_fail(tmp_path: Path) -> None:
    (tmp_path / "validation.schema.json").write_text("{ broken json", encoding="utf-8")
    assert schema_contract_check("validation", schema_dir=tmp_path).status is ResultStatus.FAIL


def test_missing_definition_returns_fail(tmp_path: Path) -> None:
    write_schema(tmp_path, "validation", {"$defs": {}})
    assert schema_contract_check("validation", schema_dir=tmp_path).status is ResultStatus.FAIL


def test_missing_required_property_returns_fail(tmp_path: Path) -> None:
    write_schema(tmp_path, "validation", {"$defs": {"SkillResult": {"properties": {}}}})
    assert schema_contract_check("validation", schema_dir=tmp_path).status is ResultStatus.FAIL


def test_forbidden_property_returns_fail(tmp_path: Path) -> None:
    schema = valid_validation_schema()
    schema["$defs"]["SkillResult"]["properties"]["human_review_required"] = {}
    write_schema(tmp_path, "validation", schema)
    assert schema_contract_check("validation", schema_dir=tmp_path).status is ResultStatus.FAIL


def test_ontology_missing_snake_property_returns_fail(tmp_path: Path) -> None:
    schema = valid_ontology_schema()
    del schema["$defs"]["ElementOccurrence"]["properties"]["element_imo_id"]
    write_schema(tmp_path, "ontology", schema)
    assert schema_contract_check("ontology", schema_dir=tmp_path).status is ResultStatus.FAIL


def test_ontology_forbidden_camel_property_returns_fail(tmp_path: Path) -> None:
    schema = valid_ontology_schema()
    schema["$defs"]["ElementOccurrence"]["properties"]["elementImoId"] = {}
    write_schema(tmp_path, "ontology", schema)
    assert schema_contract_check("ontology", schema_dir=tmp_path).status is ResultStatus.FAIL


# --- 불변조건과 직렬화 ---


def test_fail_results_require_human_review(tmp_path: Path) -> None:
    (tmp_path / "ontology.schema.json").write_text("{ broken", encoding="utf-8")
    results = [
        schema_contract_check("unknown-schema"),
        schema_contract_check("validation", schema_dir=tmp_path),
        schema_contract_check("ontology", schema_dir=tmp_path),
    ]
    for result in results:
        assert result.status is ResultStatus.FAIL
        assert result.human_review_required is True
        assert len(result.errors) >= 1


def test_pass_results_have_no_findings() -> None:
    for name in ("validation", "ontology"):
        result = schema_contract_check(name)
        assert result.status is ResultStatus.PASS
        assert result.human_review_required is False
        assert result.errors == [] and result.warnings == []


def test_returns_skill_result_instance() -> None:
    assert isinstance(schema_contract_check("validation"), SkillResult)


def test_result_serializes_with_camel_case_alias() -> None:
    dumped = schema_contract_check("validation").model_dump(by_alias=True)
    assert "humanReviewRequired" in dumped
    assert "human_review_required" not in dumped
