"""Schema Generator Contract Test (AGENTS.md §4.6).

scripts/generate_schemas.py가 src/k_mds/models에서 schemas/generated/*.schema.json을
결정론적으로 생성하는지 검증한다.

Alias 정책(고정): validation.schema.json은 camelCase(AGENTS.md §10 JSON 예시),
ontology.schema.json은 snake_case를 사용한다.
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = REPO_ROOT / "scripts" / "generate_schemas.py"
OUTPUT_DIR = REPO_ROOT / "schemas" / "generated"
ONTOLOGY_SCHEMA = OUTPUT_DIR / "ontology.schema.json"
VALIDATION_SCHEMA = OUTPUT_DIR / "validation.schema.json"


def run_generator() -> None:
    assert GENERATOR.is_file(), "scripts/generate_schemas.py가 아직 존재하지 않는다"
    result = subprocess.run(
        [sys.executable, str(GENERATOR)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr


def load_defs(path: Path) -> dict[str, Any]:
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    defs = schema.get("$defs", {})
    assert isinstance(defs, dict)
    return defs


def properties_of(defs: dict[str, Any], model_name: str) -> dict[str, Any]:
    assert model_name in defs, f"$defs에 {model_name} 정의가 없다"
    props = defs[model_name].get("properties", {})
    assert isinstance(props, dict)
    return props


def test_generator_creates_both_schema_files() -> None:
    run_generator()
    assert ONTOLOGY_SCHEMA.is_file()
    assert VALIDATION_SCHEMA.is_file()


def test_generated_files_are_valid_json() -> None:
    run_generator()
    for path in (ONTOLOGY_SCHEMA, VALIDATION_SCHEMA):
        parsed = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict), f"{path.name}은 단일 JSON Schema 객체여야 한다"


def test_validation_schema_contains_skill_result() -> None:
    run_generator()
    defs = load_defs(VALIDATION_SCHEMA)
    assert "SkillResult" in defs
    assert "Evidence" in defs
    assert "ValidationFinding" in defs


def test_skill_result_uses_camel_case_alias() -> None:
    run_generator()
    props = properties_of(load_defs(VALIDATION_SCHEMA), "SkillResult")
    assert "humanReviewRequired" in props
    assert "human_review_required" not in props


def test_validation_finding_uses_camel_case_alias() -> None:
    run_generator()
    props = properties_of(load_defs(VALIDATION_SCHEMA), "ValidationFinding")
    assert "evidenceRefs" in props
    assert "evidence_refs" not in props


def test_ontology_schema_contains_element_and_occurrence() -> None:
    run_generator()
    defs = load_defs(ONTOLOGY_SCHEMA)
    assert "DataElement" in defs
    assert "ElementOccurrence" in defs
    for model in ("Dataset", "Component", "CodeList", "BusinessRule"):
        assert model in defs


def test_validation_schema_contains_governance_result() -> None:
    # ADR-0004: GovernanceResult와 관련 Enum은 validation Schema 대상에 포함된다.
    run_generator()
    defs = load_defs(VALIDATION_SCHEMA)
    assert "GovernanceResult" in defs
    assert "GovernanceDecisionStatus" in defs
    assert "GovernanceDecisionType" in defs
    props = properties_of(defs, "GovernanceResult")
    assert "decisionId" in props
    assert "decision_id" not in props
    assert "humanReviewRequired" in props
    assert "sourceResults" in props


def test_ontology_schema_contains_source_manifest_entry() -> None:
    # ADR-0003: SourceManifestEntry는 Ontology Schema 대상에 포함된다.
    run_generator()
    defs = load_defs(ONTOLOGY_SCHEMA)
    assert "SourceManifestEntry" in defs
    props = properties_of(defs, "SourceManifestEntry")
    assert "source_hash" in props and "verified" in props


def test_ontology_schema_contains_source_manifest() -> None:
    # ADR-0006: SourceManifest와 source_hash pattern은 Ontology Schema에 반영된다.
    run_generator()
    defs = load_defs(ONTOLOGY_SCHEMA)
    assert "SourceManifest" in defs
    entry_props = properties_of(defs, "SourceManifestEntry")
    assert entry_props["source_hash"].get("pattern") == "^[0-9a-f]{64}$"


def test_occurrence_uses_snake_case_policy() -> None:
    # 고정 정책: Ontology 모델은 snake_case를 사용한다.
    run_generator()
    props = properties_of(load_defs(ONTOLOGY_SCHEMA), "ElementOccurrence")
    assert "element_imo_id" in props
    assert "elementImoId" not in props


def test_generation_is_deterministic() -> None:
    run_generator()
    first = (ONTOLOGY_SCHEMA.read_bytes(), VALIDATION_SCHEMA.read_bytes())
    run_generator()
    second = (ONTOLOGY_SCHEMA.read_bytes(), VALIDATION_SCHEMA.read_bytes())
    assert first == second


def test_output_ends_with_newline_and_has_no_absolute_paths() -> None:
    run_generator()
    for path in (ONTOLOGY_SCHEMA, VALIDATION_SCHEMA):
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n"), f"{path.name}은 마지막 newline을 포함해야 한다"
        assert "c:\\" not in text.lower() and "c:/" not in text.lower()
        assert "generated_at" not in text


def test_do_not_edit_notice_is_preserved() -> None:
    run_generator()
    notice = OUTPUT_DIR / "DO_NOT_EDIT.md"
    assert notice.is_file()
    assert "직접 수정" in notice.read_text(encoding="utf-8")


def test_no_real_imo_values_in_generated_schemas() -> None:
    run_generator()
    for path in (ONTOLOGY_SCHEMA, VALIDATION_SCHEMA):
        text = path.read_text(encoding="utf-8")
        assert re.search(r"IMO\d", text) is None, "실제 IMO ID 형태의 값이 포함되면 안 된다"
        assert re.search(r"gears", text, re.IGNORECASE) is None
        assert "TEST/PATH" not in text
