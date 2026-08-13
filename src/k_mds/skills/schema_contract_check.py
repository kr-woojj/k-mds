"""schema_contract_check Skill (ADR-0002).

생성된 JSON Schema artifact(schemas/generated)의 구조 무결성을 결정론적으로
검사하고 항상 SkillResult를 반환한다. Payload 자체는 검증하지 않는다 —
Payload 검증은 schema_validate가 담당한다. 예외를 외부로 던지지 않으며
full JSON Schema validation library를 사용하지 않는다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from k_mds.models import FindingSeverity, ResultStatus, SkillResult, ValidationFinding

RULE_ID = "urn:k-mds:rule:schema-contract-check:0.1"
VALIDATION_LEVEL = "contract-structure"

_DEFAULT_SCHEMA_DIR = Path(__file__).resolve().parents[3] / "schemas" / "generated"

#: schema_name별 최소 Contract: (정의 이름, 필수 property, 금지 property)
_CONTRACTS: dict[str, tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]] = {
    "validation": (
        ("SkillResult", ("humanReviewRequired",), ("human_review_required",)),
    ),
    "ontology": (
        ("DataElement", (), ()),
        ("ElementOccurrence", ("element_imo_id",), ("elementImoId",)),
    ),
}


def _finding(code: str, message: str, path: str | None = None) -> ValidationFinding:
    return ValidationFinding(
        severity=FindingSeverity.ERROR,
        code=code,
        message=message,
        rule_id=RULE_ID,
        path=path,
    )


def _data(schema_name: str, checked: list[str]) -> dict[str, Any]:
    return {
        "schemaName": schema_name,
        "validationLevel": VALIDATION_LEVEL,
        "checkedDefinitions": checked,
    }


def _fail(schema_name: str, errors: list[ValidationFinding]) -> SkillResult:
    return SkillResult(
        status=ResultStatus.FAIL,
        human_review_required=True,
        data=_data(schema_name, []),
        errors=errors,
    )


def schema_contract_check(
    schema_name: str,
    schema_dir: Path | None = None,
) -> SkillResult:
    """생성된 Schema artifact의 최소 구조 Contract를 검증한다.

    schema_dir은 Test에서 의도적으로 다른 경로를 주입하기 위한 선택 파라미터다.
    """
    if schema_name not in _CONTRACTS:
        supported = ", ".join(sorted(_CONTRACTS))
        return _fail(
            schema_name,
            [_finding("SCH_002", f"지원하지 않는 schema_name이다 (지원: {supported})")],
        )

    directory = schema_dir if schema_dir is not None else _DEFAULT_SCHEMA_DIR
    schema_file = f"{schema_name}.schema.json"
    schema_path = directory / schema_file

    if not schema_path.is_file():
        return _fail(
            schema_name,
            [_finding("SCH_003", f"생성된 Schema 파일이 존재하지 않는다: {schema_file}")],
        )

    try:
        schema: Any = json.loads(schema_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _fail(
            schema_name,
            [_finding("SCH_004", f"Schema 파일이 유효한 JSON이 아니다: {schema_file}")],
        )

    if not isinstance(schema, dict):
        return _fail(
            schema_name,
            [_finding("SCH_004", f"Schema는 단일 JSON Object여야 한다: {schema_file}")],
        )

    defs = schema.get("$defs")
    if not isinstance(defs, dict):
        return _fail(
            schema_name,
            [
                _finding(
                    "SCH_005",
                    f"Schema에 $defs가 존재하지 않는다: {schema_file}",
                    path="$.$defs",
                )
            ],
        )

    errors: list[ValidationFinding] = []
    checked: list[str] = []
    for definition, required_props, forbidden_props in _CONTRACTS[schema_name]:
        definition_obj = defs.get(definition)
        if not isinstance(definition_obj, dict):
            errors.append(
                _finding(
                    "SCH_006",
                    f"$defs에 {definition} 정의가 존재하지 않는다",
                    path=f"$.$defs.{definition}",
                )
            )
            continue
        properties = definition_obj.get("properties")
        properties = properties if isinstance(properties, dict) else {}
        for prop in required_props:
            if prop not in properties:
                errors.append(
                    _finding(
                        "SCH_007",
                        f"{definition}에 필수 property가 없다: {prop}",
                        path=f"$.$defs.{definition}.properties.{prop}",
                    )
                )
        for prop in forbidden_props:
            if prop in properties:
                errors.append(
                    _finding(
                        "SCH_008",
                        f"{definition}에 금지된 property가 존재한다: {prop}",
                        path=f"$.$defs.{definition}.properties.{prop}",
                    )
                )
        checked.append(definition)

    if errors:
        return _fail(schema_name, errors)

    return SkillResult(
        status=ResultStatus.PASS,
        human_review_required=False,
        data=_data(schema_name, checked),
    )
