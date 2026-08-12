"""Pydantic 원천 모델에서 JSON Schema를 결정론적으로 생성한다 (AGENTS.md §4.6).

- 원천: src/k_mds/models (ADR-0001 Single Source of Truth)
- 출력: schemas/generated/ontology.schema.json, validation.schema.json
- Alias 정책: validation은 camelCase(AGENTS.md §10), ontology는 snake_case
- 결정성: timestamp·random 미사용, sort_keys=True, 항상 동일 출력

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


def write_schema(path: Path, schema: dict[str, Any]) -> None:
    text = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text + "\n")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    targets: dict[str, dict[str, Any]] = {
        "ontology.schema.json": build_schema(
            TypeAdapter(OntologyModels), "k-mds Core Ontology Models"
        ),
        "validation.schema.json": build_schema(
            TypeAdapter(ValidationModels), "k-mds Validation Contract Models"
        ),
    }
    for filename, schema in targets.items():
        write_schema(OUTPUT_DIR / filename, schema)
        print(f"[generate-schemas] schemas/generated/{filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
