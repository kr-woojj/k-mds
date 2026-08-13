"""Pydantic 원천 모델에서 JSON Schema를 결정론적으로 생성한다 (AGENTS.md §4.6).

- 원천: src/k_mds/models (ADR-0001 Single Source of Truth)
- 출력: schemas/generated/ontology.schema.json, validation.schema.json
- Alias 정책: validation은 camelCase(AGENTS.md §10), ontology는 snake_case
- 결정성: timestamp·random 미사용, sort_keys=True, 항상 동일 출력

Public Helper(generate_schema_documents, serialize_schema, generate_to)는
check_schema_drift.py가 동일 생성 규칙을 재사용하기 위해 제공한다.
출력 파일은 직접 수정하지 않는다 (schemas/generated/DO_NOT_EDIT.md 참조).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from k_mds.models import (
    BusinessRule,
    CodeList,
    Component,
    DataElement,
    Dataset,
    ElementOccurrence,
    Evidence,
    SkillResult,
    ValidationFinding,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "schemas" / "generated"

OntologyModels = (
    Dataset | Component | DataElement | ElementOccurrence | CodeList | BusinessRule
)
ValidationModels = SkillResult | ValidationFinding | Evidence


def build_schema(adapter: TypeAdapter[Any], title: str) -> dict[str, Any]:
    schema = adapter.json_schema(by_alias=True, ref_template="#/$defs/{model}")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = title
    return schema


def generate_schema_documents() -> dict[str, dict[str, Any]]:
    """파일명 -> JSON Schema 객체. 생성 규칙의 단일 정의다."""
    return {
        "ontology.schema.json": build_schema(
            TypeAdapter(OntologyModels), "k-mds Core Ontology Models"
        ),
        "validation.schema.json": build_schema(
            TypeAdapter(ValidationModels), "k-mds Validation Contract Models"
        ),
    }


def serialize_schema(schema: dict[str, Any]) -> str:
    """결정론적 직렬화: UTF-8, indent=2, sort_keys, 마지막 newline 포함."""
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_schema(path: Path, schema: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(serialize_schema(schema))


def generate_to(output_dir: Path) -> list[str]:
    """output_dir에 전체 Schema를 생성하고 파일명 목록을 반환한다."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filenames: list[str] = []
    for filename, schema in generate_schema_documents().items():
        write_schema(output_dir / filename, schema)
        filenames.append(filename)
    return filenames


def main() -> int:
    for filename in generate_to(OUTPUT_DIR):
        print(f"[generate-schemas] schemas/generated/{filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
