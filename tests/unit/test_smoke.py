"""Repository Bootstrap 범위 Smoke Test.

패키지 인식, 원본 미확보 상태(구조적 YAML 검증), Generated 폴더 보호 안내,
경계 Local AGENTS.md 존재, Legacy 명칭 부재 등
Bootstrap 단계에서 구현된 범위만 검증한다.
"""

from pathlib import Path
from typing import Any

import yaml

import k_mds

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "data" / "raw" / "FAL50" / "source-manifest.yaml"

# 문자열 결합으로 정의하여 이 테스트 파일 자신이 검사에 걸리지 않도록 한다.
LEGACY_NAMES = ("".join(("kr-imo-", "compendium-mcp")), "".join(("kr_imo", "_mcp")))
EXCLUDED_DIRS = {".git", ".venv", ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__"}
# Root AGENTS.md의 금지사항 설명은 검사 대상에서 제외한다.
EXCLUDED_FILES = {REPO_ROOT / "AGENTS.md"}


def _load_manifest() -> dict[str, Any]:
    data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "source-manifest.yaml 최상위는 Mapping이어야 한다"
    return data


def _collect_keys(node: object) -> set[str]:
    """YAML 전체 계층의 Mapping Key를 재귀 수집한다."""
    keys: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            keys.add(str(key))
            keys |= _collect_keys(value)
    elif isinstance(node, list):
        for item in node:
            keys |= _collect_keys(item)
    return keys


def test_package_importable_with_version() -> None:
    assert k_mds.__version__ == "0.1.0"


def test_source_manifest_is_pending_source() -> None:
    manifest = _load_manifest()
    assert manifest["standard"]["fal_version"] == "FAL50"
    assert manifest["standard"]["status"] == "pending_source"
    assert manifest["files"] == []
    assert manifest["ingestion"]["status"] == "pending_source"


def test_source_manifest_has_no_sha256_key() -> None:
    # 공식 원본 미확보 상태에서는 어떤 계층에도 Hash Key(Placeholder 포함)가 없어야 한다.
    assert "sha256" not in _collect_keys(_load_manifest())


def test_generated_folders_have_do_not_edit_notice() -> None:
    for rel in ("data/normalized", "ontology/generated", "schemas/generated"):
        notice = REPO_ROOT / rel / "DO_NOT_EDIT.md"
        assert notice.is_file(), f"{rel}/DO_NOT_EDIT.md 누락"


def test_boundary_folders_have_local_agents_md() -> None:
    for rel in ("data", "ontology", "schemas", "src", "tests"):
        assert (REPO_ROOT / rel / "AGENTS.md").is_file(), f"{rel}/AGENTS.md 누락"


def test_no_legacy_project_names_in_scaffold() -> None:
    offenders: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path in EXCLUDED_FILES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(name in text for name in LEGACY_NAMES):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], f"Legacy 명칭 발견: {offenders}"
