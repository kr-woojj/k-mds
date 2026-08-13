"""schema_validate Skill Contract Test (AGENTS.md §10).

Fixture schema는 전부 테스트 내부에서 합성한 가상 구조이며
실제 IMO ID, Technical Position, KR Rule, KR GEARs Field를 사용하지 않는다.
"""

import json
from pathlib import Path
from typing import Any

from k_mds.models import ResultStatus, SkillResult
from k_mds.skills import schema_validate


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


# --- PASS 경로 (지시 Test 1~4) ---


def test_validation_schema_returns_pass() -> None:
    assert schema_validate({}, "validation").status is ResultStatus.PASS


def test_ontology_schema_returns_pass() -> None:
    assert schema_validate({}, "ontology").status is ResultStatus.PASS


def test_validation_result_data_contains_schema_name() -> None:
    assert schema_validate({}, "validation").data["schemaName"] == "validation"


def test_ontology_result_data_contains_schema_name() -> None:
    assert schema_validate({}, "ontology").data["schemaName"] == "ontology"


# --- FAIL 경로 (지시 Test 5~11) ---


def test_unsupported_schema_name_returns_fail() -> None:
    assert schema_validate({}, "unknown-schema").status is ResultStatus.FAIL


def test_missing_schema_file_returns_fail(tmp_path: Path) -> None:
    result = schema_validate({}, "validation", schema_dir=tmp_path)
    assert result.status is ResultStatus.FAIL


def test_broken_json_schema_returns_fail(tmp_path: Path) -> None:
    (tmp_path / "validation.schema.json").write_text("{ broken json", encoding="utf-8")
    assert schema_validate({}, "validation", schema_dir=tmp_path).status is ResultStatus.FAIL


def test_validation_schema_without_camel_property_returns_fail(tmp_path: Path) -> None:
    write_schema(tmp_path, "validation", {"$defs": {"SkillResult": {"properties": {}}}})
    assert schema_validate({}, "validation", schema_dir=tmp_path).status is ResultStatus.FAIL


def test_validation_schema_with_snake_property_returns_fail(tmp_path: Path) -> None:
    schema = valid_validation_schema()
    schema["$defs"]["SkillResult"]["properties"]["human_review_required"] = {}
    write_schema(tmp_path, "validation", schema)
    assert schema_validate({}, "validation", schema_dir=tmp_path).status is ResultStatus.FAIL


def test_ontology_schema_without_snake_property_returns_fail(tmp_path: Path) -> None:
    schema = valid_ontology_schema()
    del schema["$defs"]["ElementOccurrence"]["properties"]["element_imo_id"]
    write_schema(tmp_path, "ontology", schema)
    assert schema_validate({}, "ontology", schema_dir=tmp_path).status is ResultStatus.FAIL


def test_ontology_schema_with_camel_property_returns_fail(tmp_path: Path) -> None:
    schema = valid_ontology_schema()
    schema["$defs"]["ElementOccurrence"]["properties"]["elementImoId"] = {}
    write_schema(tmp_path, "ontology", schema)
    assert schema_validate({}, "ontology", schema_dir=tmp_path).status is ResultStatus.FAIL


def test_non_dict_payload_returns_fail() -> None:
    result = schema_validate("not-a-dict", "validation")  # type: ignore[arg-type]
    assert result.status is ResultStatus.FAIL


# --- 불변조건과 직렬화 (지시 Test 12~15) ---


def _fail_results(tmp_path: Path) -> list[SkillResult]:
    (tmp_path / "ontology.schema.json").write_text("{ broken", encoding="utf-8")
    return [
        schema_validate({}, "unknown-schema"),
        schema_validate({}, "validation", schema_dir=tmp_path),
        schema_validate({}, "ontology", schema_dir=tmp_path),
    ]


def test_all_fail_results_require_human_review(tmp_path: Path) -> None:
    for result in _fail_results(tmp_path):
        assert result.status is ResultStatus.FAIL
        assert result.human_review_required is True
        assert len(result.errors) >= 1


def test_all_pass_results_have_no_findings() -> None:
    for name in ("validation", "ontology"):
        result = schema_validate({}, name)
        assert result.status is ResultStatus.PASS
        assert result.human_review_required is False
        assert result.errors == [] and result.warnings == []


def test_returns_skill_result_instance() -> None:
    assert isinstance(schema_validate({}, "validation"), SkillResult)


def test_result_serializes_with_camel_case_alias() -> None:
    dumped = schema_validate({}, "validation").model_dump(by_alias=True)
    assert "humanReviewRequired" in dumped
    assert "human_review_required" not in dumped
