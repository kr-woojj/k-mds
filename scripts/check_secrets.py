"""커밋 전 비밀정보·내부정보 검사 (AGENTS.md: .env·인증서·실선 데이터는 git 에 올리지 않는다).

표준 라이브러리만 쓴다. 값은 출력하지 않고 앞 3자만 남겨 가린다.

사용:
  python scripts/check_secrets.py --staged      # 커밋 대기(index) 파일만 — pre-commit 훅이 호출
  python scripts/check_secrets.py --all         # 추적 중인 전체 파일 — CI
  python scripts/check_secrets.py <경로...>      # 지정 파일

설치(한 번): git config core.hooksPath scripts/githooks
예외: 검사 대상이 아닌 줄에는 `secrets-allow` 를 주석으로 적는다.
종료 코드: 0 이상 없음 / 1 발견 / 2 실행 오류
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 2_000_000
ALLOW_MARK = "secrets-allow"

# 저장소에 들어가면 안 되는 경로 (k-mds/.gitignore 와 같은 기준)
FORBIDDEN_PATHS: tuple[tuple[str, str], ...] = (
    ("env-file", r"(^|/)\.env(\.(?!example$)[^/]*)?$"),
    ("pm-work-files", r"^pm/(meetings|tools)/(?!\.gitkeep$)"),
    ("evidence-private", r"^verification/evidence-private/"),
    ("project-docs", r"^docs/\(RS-"),
    ("key-material", r"\.(pem|p12|pfx|jks|key|keystore|truststore)$"),
)

# 내용 규칙: (이름, 정규식). 첫 번째 그룹이 있으면 그 부분을 가려서 보여준다.
CONTENT_RULES: tuple[tuple[str, str], ...] = (
    (
        "api-key-literal",
        r"(AIza[0-9A-Za-z_-]{30,}|sk-(?:proj-|ant-|or-)?[A-Za-z0-9_-]{20,}"
        r"|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}"
        r"|hf_[A-Za-z0-9]{30,}|r8_[A-Za-z0-9]{30,}|tvly-[A-Za-z0-9-]{20,})",
    ),
    (
        # 이름이 자격증명처럼 생겼고(API_KEY·SECRET·TOKEN·PASSWORD), 값도 자격증명처럼 생긴 경우만:
        # 숫자 포함 12자 이상 또는 24자 이상. 자리표시자(<…>, ${…})·코드(os.…)·test/dummy 값은 제외.
        "secret-assignment",
        r"(?i)(?:\b[A-Z][A-Z0-9_]*(?:API_KEY|SECRET|TOKEN|PASSWORD|PASSWD)[A-Z0-9_]*"
        r"|\b(?:api_?key|secret|password|passwd|access_token|token))[\"']?\s*[=:]\s*[\"']?"
        r"(?!test|dummy|example|sample|<|\$|\{|os\.)"
        r"((?=[A-Za-z0-9_\-./+=]*\d)[A-Za-z0-9_\-./+=]{12,}|[A-Za-z0-9_\-./+=]{24,})",
    ),
    ("ids-credential", r"IDS_CONNECTOR_(?:USER|PASSWORD)\s*[=:]\s*[\"']?([^\s\"'<$#{]{3,})"),
    ("private-ip", r"\b((?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3})\b"),
    ("ip-url", r"https?://((?!127\.0\.0\.1|0\.0\.0\.0)\d{1,3}(?:\.\d{1,3}){3})"),
    ("partner-host", r"https?://([^\s\"'<>]*(?:nexawave|vessellink|ngrok)[^\s\"'<>]*)"),
)
# 값이 아니라 이름만 적는 줄은 통과시킨다 (예: 설명문의 'TOKEN=' 뒤에 아무것도 없음)
SKIP_FILES = ("scripts/check_secrets.py",)


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int
    sample: str


def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def _mask(value: str) -> str:
    return value[:3] + "…" if len(value) > 3 else "…"


def _is_binary(data: bytes) -> bool:
    return b"\x00" in data[:8192]


def _scan_path_name(path: str) -> Finding | None:
    for name, pattern in FORBIDDEN_PATHS:
        if re.search(pattern, path):
            return Finding(name, path, 0, "(경로 자체가 금지 대상)")
    return None


def _scan_content(path: str, data: bytes) -> list[Finding]:
    if path in SKIP_FILES or path.endswith(".example") or _is_binary(data):
        return []
    text = data.decode("utf-8", errors="replace")
    out: list[Finding] = []
    for no, line in enumerate(text.splitlines(), 1):
        if ALLOW_MARK in line:
            continue
        for name, pattern in CONTENT_RULES:
            m = re.search(pattern, line)
            if m:
                out.append(Finding(name, path, no, _mask(m.group(1) if m.groups() else m.group(0))))
                break
    return out


def _targets(args: argparse.Namespace) -> list[tuple[str, bytes]]:
    if args.staged:
        raw = _git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
        paths = [p for p in raw.decode("utf-8", "surrogateescape").split("\0") if p]
        return [(p, _git("show", f":{p}")) for p in paths]
    if args.all:
        raw = _git("ls-files", "-z")
        paths = [p for p in raw.decode("utf-8", "surrogateescape").split("\0") if p]
    else:
        paths = [Path(p).resolve().relative_to(ROOT).as_posix() for p in args.paths]
    out: list[tuple[str, bytes]] = []
    for p in paths:
        f = ROOT / p
        if f.is_file() and f.stat().st_size <= MAX_BYTES:
            out.append((p, f.read_bytes()))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--staged", action="store_true", help="커밋 대기 파일만")
    g.add_argument("--all", action="store_true", help="추적 중인 전체 파일")
    parser.add_argument("paths", nargs="*", help="검사할 파일")
    args = parser.parse_args(argv)
    if not (args.staged or args.all or args.paths):
        parser.error("--staged, --all, 또는 경로가 필요하다")
    try:
        targets = _targets(args)
    except subprocess.CalledProcessError as exc:
        print(f"git 실행 실패: {exc}", file=sys.stderr)
        return 2
    findings: list[Finding] = []
    for path, data in targets:
        bad = _scan_path_name(path)
        if bad:
            findings.append(bad)
            continue
        findings.extend(_scan_content(path, data))
    if not findings:
        print(f"check_secrets: 이상 없음 ({len(targets)} 파일)")
        return 0
    print(f"check_secrets: {len(findings)}건 발견 — 커밋을 중단한다. 값은 가려서 표시한다.")
    for f in findings:
        where = f"{f.path}:{f.line}" if f.line else f.path
        print(f"  [{f.rule}] {where}  {f.sample}")
    print("예외가 맞으면 해당 줄에 'secrets-allow' 주석을 적거나 파일을 .gitignore 에 올린다.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
