"""Schema Drift Gate Test (AGENTS.md §2.5).

tmp_path의 synthetic Schema만 사용한다. 실제 generated Schema는 읽기 전용으로만
접근하며 수정 후 복원하는 방식을 사용하지 않는다. subprocess는 dev.py CLI
Test(11~12)에만 제한한다.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
GENERATED_DIR = REPO_ROOT / "schemas" / "generated"
SCHEMA_FILES = ("ontology.schema.json", "validation.schema.json")

sys.path.insert(0, str(SCRIPTS_DIR))

import check_schema_drift  # noqa: E402
import generate_schemas  # noqa: E402


def make_synced_dir(tmp_path: Path) -> Path:
    generate_schemas.generate_to(tmp_path)
    return tmp_path


def run_main(monkeypatch: pytest.MonkeyPatch, generated_dir: Path) -> int:
    monkeypatch.setenv("K_MDS_GENERATED_DIR", str(generated_dir))
    return check_schema_drift.main()


# --- 지시 Test 1~5: exit code ---


def test_identical_schemas_exit_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert run_main(monkeypatch, make_synced_dir(tmp_path)) == 0


def test_drifted_ontology_exit_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_synced_dir(tmp_path)
    (tmp_path / "ontology.schema.json").write_text("{}\n", encoding="utf-8")
    assert run_main(monkeypatch, tmp_path) == 1


def test_drifted_validation_exit_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_synced_dir(tmp_path)
    (tmp_path / "validation.schema.json").write_text("{}\n", encoding="utf-8")
    assert run_main(monkeypatch, tmp_path) == 1


def test_missing_ontology_exit_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_synced_dir(tmp_path)
    (tmp_path / "ontology.schema.json").unlink()
    assert run_main(monkeypatch, tmp_path) == 1


def test_missing_validation_exit_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    make_synced_dir(tmp_path)
    (tmp_path / "validation.schema.json").unlink()
    assert run_main(monkeypatch, tmp_path) == 1


# --- 지시 Test 6~8: 출력 내용 ---


def test_drift_output_contains_filename_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    make_synced_dir(tmp_path)
    (tmp_path / "ontology.schema.json").write_text("{}\n", encoding="utf-8")
    assert run_main(monkeypatch, tmp_path) == 1
    out = capsys.readouterr().out
    assert "ontology.schema.json" in out
    # 파일 본문 전체를 출력하지 않는다 (Schema 본문 marker 부재).
    assert "$defs" not in out and "$schema" not in out
    # Repository 절대경로를 출력하지 않는다.
    assert str(REPO_ROOT).lower() not in out.lower()
    assert "c:\\" not in out.lower() and "c:/" not in out.lower()


# --- 지시 Test 9: 결정성 ---


def test_generation_is_byte_deterministic(tmp_path: Path) -> None:
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    generate_schemas.generate_to(dir_a)
    generate_schemas.generate_to(dir_b)
    for filename in SCHEMA_FILES:
        assert (dir_a / filename).read_bytes() == (dir_b / filename).read_bytes()


# --- 지시 Test 10: committed 파일 무변경 ---


def test_check_does_not_modify_committed_schemas() -> None:
    before = {name: (GENERATED_DIR / name).read_bytes() for name in SCHEMA_FILES}
    check_schema_drift.check_drift(GENERATED_DIR)
    after = {name: (GENERATED_DIR / name).read_bytes() for name in SCHEMA_FILES}
    assert before == after


# --- Git EOL 정책 Regression (파일을 수정하지 않는 읽기 전용 검사) ---


def test_generated_schemas_are_git_attributed_lf() -> None:
    for filename in SCHEMA_FILES:
        result = subprocess.run(
            ["git", "check-attr", "eol", "--", f"schemas/generated/{filename}"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip().endswith("eol: lf"), result.stdout


# --- 지시 Test 11~12: dev.py CLI (subprocess 허용 범위) ---


def run_dev_check(extra_env: dict[str, str] | None = None) -> "subprocess.CompletedProcess[str]":
    env = os.environ.copy()
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "dev.py"), "check-schemas"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )


def test_dev_check_schemas_exit_zero() -> None:
    result = run_dev_check()
    assert result.returncode == 0, result.stdout + result.stderr


def test_dev_check_schemas_exit_one_on_drift(tmp_path: Path) -> None:
    make_synced_dir(tmp_path)
    (tmp_path / "validation.schema.json").write_text("{}\n", encoding="utf-8")
    result = run_dev_check({"K_MDS_GENERATED_DIR": str(tmp_path)})
    assert result.returncode == 1, result.stdout + result.stderr
