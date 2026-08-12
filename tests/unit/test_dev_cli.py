"""scripts/dev.py Subcommand Contract Test.

dev.py는 Working Directory에 의존하지 않아야 하므로
모든 호출을 Repository 외부 임시 폴더에서 수행한다.

주의: validate와 test Subcommand는 내부에서 Pytest를 재귀 실행하므로
이 파일에서는 호출하지 않는다 (수동 및 CI에서 검증).
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_PY = REPO_ROOT / "scripts" / "dev.py"


def _run_dev(command: str, cwd: Path) -> "subprocess.CompletedProcess[str]":
    assert DEV_PY.is_file(), "scripts/dev.py가 아직 존재하지 않는다"
    return subprocess.run(
        [sys.executable, str(DEV_PY), command],
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )


def test_build_subcommand_exits_zero(tmp_path: Path) -> None:
    result = _run_dev("build", cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_run_mcp_subcommand_exits_two(tmp_path: Path) -> None:
    result = _run_dev("run-mcp", cwd=tmp_path)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "구현되지 않" in (result.stdout + result.stderr)
