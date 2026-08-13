"""Output Root Binding Contract Test (ADR-0010 Amendment).

실제 FAL50, Actual Binding, Actual Report에는 접근하지 않는다.
모든 값은 TEST 표기의 Synthetic Fixture다.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from k_mds.models import OutputRootBinding

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_normalization_authorization as validator_module  # noqa: E402
from test_normalization_authorization import (  # noqa: E402
    make_auth,
    make_report,
    run,
)


def make_binding(root_path: Path, **overrides: Any) -> dict[str, Any]:
    binding: dict[str, Any] = {
        "version": 1,
        "rootId": "TEST-RESTRICTED-ROOT-001",
        "storageClass": "internal-restricted",
        "rootPath": str(root_path),
    }
    binding.update(overrides)
    return binding


def run_with_binding(
    tmp_path: Path,
    *,
    binding: dict[str, Any] | None = None,
    output_dir: Any = None,
    repository_root: Any = None,
    auth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = tmp_path / "restricted-root"
    root.mkdir(exist_ok=True)
    out = output_dir if output_dir is not None else root / "out"
    if isinstance(out, Path) and not out.exists():
        out.mkdir(parents=True, exist_ok=True)
    return run(
        make_report(),
        auth if auth is not None else make_auth(),
        output_root_binding=binding if binding is not None else make_binding(root),
        output_dir=out,
        repository_root=repository_root if repository_root is not None else REPO_ROOT,
    )


def codes(result: dict[str, Any]) -> list[str]:
    return [finding["code"] for finding in result["findings"]]


# --- Binding 성공·불일치 ---


def test_matching_binding_succeeds(tmp_path: Path) -> None:
    result = run_with_binding(tmp_path)
    assert result["valid"] is True
    assert result["outputRootAuthorized"] is True


def test_binding_id_mismatch_fails(tmp_path: Path) -> None:
    root = tmp_path / "restricted-root"
    root.mkdir()
    binding = make_binding(root, rootId="TEST-RESTRICTED-ROOT-OTHER")
    result = run_with_binding(tmp_path, binding=binding)
    assert result["valid"] is False
    assert "OUTPUT_ROOT_ID_MISMATCH" in codes(result)


def test_invalid_storage_class_fails(tmp_path: Path) -> None:
    root = tmp_path / "restricted-root"
    root.mkdir()
    binding = make_binding(root, storageClass="public")
    result = run_with_binding(tmp_path, binding=binding)
    assert result["valid"] is False
    assert "OUTPUT_ROOT_BINDING_INVALID" in codes(result)


def test_relative_root_path_model_raises() -> None:
    with pytest.raises(ValidationError):
        OutputRootBinding.model_validate(make_binding(Path("relative/root")))


def test_output_under_root_succeeds(tmp_path: Path) -> None:
    root = tmp_path / "restricted-root"
    nested = root / "nested" / "out"
    nested.mkdir(parents=True)
    result = run_with_binding(tmp_path, output_dir=nested)
    assert result["valid"] is True


def test_output_outside_root_fails(tmp_path: Path) -> None:
    outside = tmp_path / "outside-out"
    outside.mkdir()
    result = run_with_binding(tmp_path, output_dir=outside)
    assert result["valid"] is False
    assert "OUTPUT_DIR_OUTSIDE_APPROVED_ROOT" in codes(result)


def test_symlink_escape_fails(tmp_path: Path) -> None:
    root = tmp_path / "restricted-root"
    root.mkdir()
    outside = tmp_path / "escape-target"
    outside.mkdir()
    link = root / "link-out"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("이 환경에서는 Symlink 생성이 지원되지 않는다")
    result = run_with_binding(tmp_path, output_dir=link)
    assert result["valid"] is False
    assert "OUTPUT_DIR_OUTSIDE_APPROVED_ROOT" in codes(result)


# --- Repository 경로 정책 ---


def test_repository_root_output_fails(tmp_path: Path) -> None:
    binding = make_binding(REPO_ROOT)
    result = run_with_binding(
        tmp_path, binding=binding, output_dir=REPO_ROOT, repository_root=REPO_ROOT
    )
    assert result["valid"] is False
    assert "OUTPUT_DIR_NOT_RESTRICTED" in codes(result)


def test_data_raw_output_fails(tmp_path: Path) -> None:
    binding = make_binding(REPO_ROOT)
    result = run_with_binding(
        tmp_path,
        binding=binding,
        output_dir=REPO_ROOT / "data" / "raw",
        repository_root=REPO_ROOT,
    )
    assert result["valid"] is False
    assert "OUTPUT_DIR_NOT_RESTRICTED" in codes(result)


def test_ignored_data_normalized_output_succeeds(tmp_path: Path) -> None:
    out = REPO_ROOT / "data" / "normalized" / f"TEST-BIND-{os.getpid()}"
    out.mkdir(parents=True)
    try:
        binding = make_binding(REPO_ROOT / "data" / "normalized")
        result = run_with_binding(
            tmp_path, binding=binding, output_dir=out, repository_root=REPO_ROOT
        )
        assert result["valid"] is True
        assert result["outputRootAuthorized"] is True
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_non_ignored_repository_output_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = REPO_ROOT / "data" / "normalized" / f"TEST-BIND-NI-{os.getpid()}"
    out.mkdir(parents=True)
    original = validator_module._git_check

    def _not_ignored(
        repo_root: Path, args: list[str]
    ) -> "subprocess.CompletedProcess[str]":
        if args and args[0] == "check-ignore":
            return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="")
        return original(repo_root, args)

    monkeypatch.setattr(validator_module, "_git_check", _not_ignored)
    try:
        binding = make_binding(REPO_ROOT / "data" / "normalized")
        result = run_with_binding(
            tmp_path, binding=binding, output_dir=out, repository_root=REPO_ROOT
        )
        assert result["valid"] is False
        assert "OUTPUT_DIR_NOT_IGNORED" in codes(result)
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_tracked_output_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = REPO_ROOT / "data" / "normalized" / f"TEST-BIND-TR-{os.getpid()}"
    out.mkdir(parents=True)
    original = validator_module._git_check

    def _tracked(repo_root: Path, args: list[str]) -> "subprocess.CompletedProcess[str]":
        if args and args[0] == "ls-files":
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="TEST-TRACKED\n", stderr=""
            )
        return original(repo_root, args)

    monkeypatch.setattr(validator_module, "_git_check", _tracked)
    try:
        binding = make_binding(REPO_ROOT / "data" / "normalized")
        result = run_with_binding(
            tmp_path, binding=binding, output_dir=out, repository_root=REPO_ROOT
        )
        assert result["valid"] is False
        assert "OUTPUT_DIR_TRACKED" in codes(result)
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_staged_output_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = REPO_ROOT / "data" / "normalized" / f"TEST-BIND-ST-{os.getpid()}"
    out.mkdir(parents=True)
    original = validator_module._git_check

    def _staged(repo_root: Path, args: list[str]) -> "subprocess.CompletedProcess[str]":
        if args and args[0] == "diff":
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="TEST-STAGED\n", stderr=""
            )
        return original(repo_root, args)

    monkeypatch.setattr(validator_module, "_git_check", _staged)
    try:
        binding = make_binding(REPO_ROOT / "data" / "normalized")
        result = run_with_binding(
            tmp_path, binding=binding, output_dir=out, repository_root=REPO_ROOT
        )
        assert result["valid"] is False
        assert "OUTPUT_DIR_STAGED" in codes(result)
    finally:
        shutil.rmtree(out, ignore_errors=True)


# --- 비노출과 Runtime Boundary ---


def test_result_does_not_contain_paths(tmp_path: Path) -> None:
    success = run_with_binding(tmp_path)
    outside = tmp_path / "outside-out"
    outside.mkdir()
    failure = run_with_binding(tmp_path, output_dir=outside)
    for result in (success, failure):
        serialized = json.dumps(result, ensure_ascii=False, sort_keys=True)
        assert str(tmp_path).lower() not in serialized.lower()
        assert str(REPO_ROOT).lower() not in serialized.lower()
        assert "c:\\" not in serialized.lower() and "c:/" not in serialized.lower()


def test_binding_not_object_fails(tmp_path: Path) -> None:
    result = run_with_binding(tmp_path, binding="TEST-MARKER-BINDING")  # type: ignore[arg-type]
    assert result["valid"] is False


def test_output_dir_not_path_fails(tmp_path: Path) -> None:
    result = run_with_binding(tmp_path, output_dir="TEST-MARKER-OUT")
    assert result["valid"] is False
    assert "OUTPUT_DIR_NOT_PATH" in codes(result)


def test_repository_root_not_path_fails(tmp_path: Path) -> None:
    result = run_with_binding(tmp_path, repository_root="TEST-MARKER-REPO")
    assert result["valid"] is False


def test_binding_failures_do_not_raise_and_deterministic(tmp_path: Path) -> None:
    outside = tmp_path / "outside-out"
    outside.mkdir()
    first = run_with_binding(tmp_path, output_dir=outside)
    second = run_with_binding(tmp_path, output_dir=outside)
    assert first == second
    for finding in first["findings"]:
        assert finding["actualValue"] is None
    serialized = json.dumps(first, ensure_ascii=False, sort_keys=True)
    assert "TEST-MARKER" not in serialized
    assert "builtins." not in serialized
