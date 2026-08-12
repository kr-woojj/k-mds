"""k-mds Cross-platform 개발 명령 인터페이스 (Repository Bootstrap 단계).

Windows, Linux, VSCode Task, Makefile 및 CI가 동일한 검증 로직을 사용하도록
단일 진입점을 제공한다.

실행 계약:
- Repository Root는 이 파일 위치 기준으로 계산하며 Working Directory에 의존하지 않는다.
- 각 Subcommand는 정수 Exit Code를 반환하고 외부 명령의 Exit Code를 보존한다.
- subprocess는 shell=True 없이 인자 배열로만 호출한다.
"""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run(args: list[str]) -> int:
    """외부 명령을 Repository Root에서 실행하고 Exit Code를 보존한다."""
    print(f"[dev] $ {' '.join(args)}", flush=True)
    return subprocess.run(args, cwd=REPO_ROOT).returncode


def _run_pytest() -> int:
    return _run(["uv", "run", "pytest"])


def cmd_setup() -> int:
    """의존성 설치."""
    return _run(["uv", "sync"])


def cmd_build() -> int:
    """src Bytecode Compile 검사 및 k_mds Package Import 검증."""
    code = _run(["uv", "run", "python", "-m", "compileall", "-q", str(REPO_ROOT / "src")])
    if code != 0:
        return code
    return _run(
        ["uv", "run", "python", "-c", "import k_mds; print('k_mds', k_mds.__version__)"]
    )


def cmd_validate() -> int:
    """최종 Quality Gate: Ruff -> MyPy -> Pytest 순서로 실행, 최초 실패 Exit Code 반환."""
    steps: list[Callable[[], int]] = [
        lambda: _run(["uv", "run", "ruff", "check", "src", "tests", "scripts"]),
        lambda: _run(["uv", "run", "mypy"]),
        _run_pytest,
    ]
    for step in steps:
        code = step()
        if code != 0:
            return code
    return 0


def cmd_test() -> int:
    """Test 전용 명령 (validate와 동일한 Pytest 실행 함수를 공유한다)."""
    return _run_pytest()


def cmd_run_mcp() -> int:
    """MCP Server 미구현 안내 (Bootstrap 단계)."""
    print("[dev] MCP Server는 아직 구현되지 않았다 (Repository Bootstrap 단계).")
    print("[dev] 선행 조건: src/k_mds/mcp/server.py 구현 (AGENTS.md §12).")
    return 2


COMMANDS: dict[str, Callable[[], int]] = {
    "setup": cmd_setup,
    "build": cmd_build,
    "validate": cmd_validate,
    "test": cmd_test,
    "run-mcp": cmd_run_mcp,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="dev.py",
        description="k-mds Bootstrap 검증 명령 (Makefile, VSCode Task, CI 공용 진입점)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, func in COMMANDS.items():
        subparsers.add_parser(name, help=func.__doc__)
    args = parser.parse_args()
    return COMMANDS[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
