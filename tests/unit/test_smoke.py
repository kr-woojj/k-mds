"""Repository Bootstrap 범위 Smoke Test.

패키지 인식, FAL50 원본 Manifest 정합성(sha256), Generated 폴더 보호 안내,
경계 Local AGENTS.md 존재, Legacy 명칭 부재 등
Bootstrap 단계에서 구현된 범위만 검증한다.
"""

import hashlib
import re
from pathlib import Path
from typing import Any

import pytest
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


def test_package_importable_with_version() -> None:
    assert k_mds.__version__ == "0.1.0"


def test_source_manifest_is_approved_with_hashed_files() -> None:
    # 2026-09-12 FAL50 원본 배치 이후: approved 상태이고 파일마다 sha256 이 있어야 한다.
    manifest = _load_manifest()
    assert manifest["standard"]["fal_version"] == "FAL50"
    assert manifest["standard"]["status"] == "approved"
    assert manifest["files"], "approved 인데 files 가 비어 있다"
    for entry in manifest["files"]:
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), entry["name"]


def test_source_manifest_hashes_match_files_on_disk() -> None:
    # 원본 xlsx/pdf 는 git 에 없으므로(data/raw/ 제외) 배치된 환경에서만 검사한다.
    manifest = _load_manifest()
    present = [e for e in manifest["files"] if (MANIFEST_PATH.parent / e["name"]).is_file()]
    if not present:
        pytest.skip("FAL50 원본 파일 미배치")
    for entry in present:
        digest = hashlib.sha256((MANIFEST_PATH.parent / entry["name"]).read_bytes()).hexdigest()
        assert digest == entry["sha256"], entry["name"]


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
