"""공용 테스트 fixture.

- 실제 FAL50 registry(var/registry.sqlite3)와 실제 validator Skill 을 사용한다.
- registry 가 없으면 관련 테스트는 명시적으로 skip 된다 (성공 위장 금지).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ghg_agent.adapters.skill_adapter import ImoMappingSkillAdapter
from ghg_agent.config import PROJECT_ROOT, Settings
from ghg_agent.reference.lookup import ReferenceLookup

FIXTURES = Path(__file__).parent / "fixtures"
REGISTRY_DB = PROJECT_ROOT / "var" / "registry.sqlite3"
SKILL_PATH = PROJECT_ROOT.parent / "imo-compendium-mapping-validator"

requires_registry = pytest.mark.skipif(
    not REGISTRY_DB.is_file(), reason="FAL50 registry 미적재 (tools/prepare_registry.py 필요)"
)
requires_skill = pytest.mark.skipif(
    not SKILL_PATH.is_dir(), reason="imo-compendium-mapping-validator 미존재"
)


def load_fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def load_fixture_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def reference() -> ReferenceLookup:
    if not REGISTRY_DB.is_file():
        pytest.skip("registry 미적재")
    lookup = ReferenceLookup(
        registry_db_path=REGISTRY_DB,
        version="FAL50",
        alias_config_path=PROJECT_ROOT / "src" / "ghg_agent" / "reference" / "aliases.json",
        code_lists_path=PROJECT_ROOT / "var" / "reference" / "code_lists.json",
    )
    lookup.load()
    return lookup


@pytest.fixture(scope="session")
def skill() -> ImoMappingSkillAdapter:
    if not (REGISTRY_DB.is_file() and SKILL_PATH.is_dir()):
        pytest.skip("skill/registry 미준비")
    return ImoMappingSkillAdapter(
        skill_path=SKILL_PATH, registry_db_path=REGISTRY_DB, timeout_seconds=60.0
    )


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        audit_log_dir=tmp_path / "evidence",
        imo_mapping_skill_path=SKILL_PATH,
        registry_db_path=REGISTRY_DB,
        code_lists_path=PROJECT_ROOT / "var" / "reference" / "code_lists.json",
        alias_config_path=PROJECT_ROOT / "src" / "ghg_agent" / "reference" / "aliases.json",
    )


def nonexistent_imo_number(reference: ReferenceLookup) -> str:
    """fixture 최대 번호 + 1 — 실존하지 않는 유효 형식 식별자 (validator 테스트 정책 준용)."""
    numbers = sorted(int(n[3:]) for n in reference._elements)
    return f"IMO{numbers[-1] + 1:04d}"
