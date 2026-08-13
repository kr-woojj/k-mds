"""data/.gitignore 파생데이터 보호 정책 Regression Test (ADR-0008).

실제 FAL50 원본과 Local Restricted Manifest에는 접근하지 않는다.
Dummy File은 TEST Marker만 사용하며 try/finally로 반드시 정리한다.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_GITIGNORE = REPO_ROOT / "data" / ".gitignore"
# 병렬 실행 충돌을 피하기 위한 프로세스 고유 Directory 이름.
DUMMY_DIR = REPO_ROOT / "data" / "normalized" / f"TEST-IGNORE-CHECK-{os.getpid()}"

DUMMY_CONTENT = '{\n  "fixture": "TEST-NORMALIZED-IGNORE-CHECK"\n}\n'
DUMMY_FILES = (
    "test.json",
    "test.csv",
    "mapping-evidence.local.json",
    "nested/test.parquet",
    "nested/test.log",
)


def _require_git_repo() -> None:
    if not (REPO_ROOT / ".git").exists():
        pytest.skip("Git Repository가 아닌 환경에서는 Ignore 정책을 검증할 수 없다")


def _git(*args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, cwd=str(REPO_ROOT)
    )


def test_data_gitignore_rules_exist() -> None:
    assert DATA_GITIGNORE.is_file()
    text = DATA_GITIGNORE.read_text(encoding="utf-8")
    # normalized 보호 규칙 (ADR-0008)
    assert "normalized/**/*" in text
    assert "!normalized/**/" in text
    assert "!normalized/**/.gitkeep" in text
    # 기존 raw 보호 규칙 유지 (ADR-0007)
    assert "raw/**/*" in text
    assert "!raw/**/source-manifest.yaml" in text


def test_normalized_dummy_files_are_ignored() -> None:
    _require_git_repo()
    try:
        (DUMMY_DIR / "nested").mkdir(parents=True)
        for rel in DUMMY_FILES:
            target = DUMMY_DIR / rel
            target.write_text(DUMMY_CONTENT, encoding="utf-8")
        for rel in DUMMY_FILES:
            rel_path = (DUMMY_DIR / rel).relative_to(REPO_ROOT).as_posix()
            result = _git("check-ignore", rel_path)
            assert result.returncode == 0, f"{rel} 이(가) ignore되지 않았다"
        status = _git("status", "--short", "--", "data/normalized").stdout
        assert "TEST-IGNORE-CHECK" not in status
    finally:
        shutil.rmtree(DUMMY_DIR, ignore_errors=True)


def test_gitkeep_and_do_not_edit_are_not_ignored() -> None:
    _require_git_repo()
    # 존재하지 않는 경로에도 check-ignore 규칙 평가는 동작한다.
    keep = _git("check-ignore", "data/normalized/.gitkeep")
    assert keep.returncode == 1, ".gitkeep은 ignore되면 안 된다"
    marker = _git("check-ignore", "data/normalized/DO_NOT_EDIT.md")
    assert marker.returncode == 1, "DO_NOT_EDIT.md는 ignore되면 안 된다"
    manifest = _git("check-ignore", "data/raw/FAL50/source-manifest.yaml")
    assert manifest.returncode == 1, "raw의 source-manifest.yaml 예외는 유지되어야 한다"


def test_no_tracked_normalized_data_files() -> None:
    _require_git_repo()
    tracked = [
        line
        for line in _git("ls-files", "--", "data/normalized").stdout.splitlines()
        if line.strip()
    ]
    # Repository가 관리하는 정책 마커만 허용한다.
    assert set(tracked) <= {"data/normalized/DO_NOT_EDIT.md"}


def test_no_staged_normalized_files() -> None:
    _require_git_repo()
    staged = _git("diff", "--cached", "--name-only", "--", "data/normalized").stdout.strip()
    assert staged == ""
