"""Registry CLI.

사용:
  python -m app.registry import --file <export> --version <V> [--db PATH] [--dry-run]
  python -m app.registry diff   --from <V1> --to <V2> [--db PATH] [--json]

출력은 key=value 라인(결정론)이며, 원본 데이터 값 원문을 출력하지 않는다.
Exit code: 0=성공, 1=검증/적재 실패, 2=사용법 오류.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.registry.database import init_db, make_session_factory
from app.registry.diff import DiffError, diff_versions
from app.registry.loader import run_import

DEFAULT_DB = Path("registry.sqlite3")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.registry",
        description="IMO Compendium Registry 적재·비교 CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser(
        "import", help="공식 export 파일을 immutable snapshot으로 적재"
    )
    import_parser.add_argument("--file", type=Path, required=True)
    import_parser.add_argument("--version", required=True)
    import_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="검증·해시·요약만 수행하고 Registry에 쓰지 않는다",
    )

    diff_parser = subparsers.add_parser("diff", help="두 버전 snapshot 비교")
    diff_parser.add_argument("--from", dest="from_version", required=True)
    diff_parser.add_argument("--to", dest="to_version", required=True)
    diff_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    diff_parser.add_argument(
        "--json", action="store_true", help="diff 결과를 JSON 한 줄로 출력"
    )
    return parser


def _command_import(args: argparse.Namespace) -> int:
    if not args.file.is_file():
        print("error=FILE_NOT_FOUND")
        return 2
    engine = init_db(args.db)
    session_factory = make_session_factory(engine)
    result = run_import(
        session_factory, args.file, args.version, dry_run=args.dry_run
    )
    print(f"command=import")
    print(f"version={result.version}")
    print(f"sourceFormat={result.source_format}")
    print(f"sourceHash={result.source_hash}")
    print(f"dryRun={str(result.dry_run).lower()}")
    print(f"ok={str(result.ok).lower()}")
    print(f"committed={str(result.committed).lower()}")
    print(f"elementCount={result.element_count}")
    print(f"occurrenceCount={result.occurrence_count}")
    print(f"issueCount={len(result.issues)}")
    for issue in result.issues:
        subject = issue.imo_data_number or "-"
        print(f"issue code={issue.code} row={issue.row} subject={subject}")
    return 0 if result.ok else 1


def _command_diff(args: argparse.Namespace) -> int:
    engine = init_db(args.db)
    session_factory = make_session_factory(engine)
    try:
        diff = diff_versions(session_factory, args.from_version, args.to_version)
    except DiffError as error:
        print(f"error=VERSION_NOT_LOADED detail={error}")
        return 1
    payload = diff.to_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0
    print("command=diff")
    print(f"fromVersion={payload['fromVersion']}")
    print(f"toVersion={payload['toVersion']}")
    print(f"addedCount={payload['addedCount']}")
    print(f"modifiedCount={payload['modifiedCount']}")
    print(f"deprecatedCount={payload['deprecatedCount']}")
    for number in payload["added"]:  # type: ignore[union-attr]
        print(f"added number={number}")
    for item in payload["modified"]:  # type: ignore[union-attr]
        fields = ",".join(item["changedFields"])
        print(f"modified number={item['imoDataNumber']} fields={fields}")
    for number in payload["deprecated"]:  # type: ignore[union-attr]
        print(f"deprecated number={number}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_error:
        return 2 if exit_error.code not in (0, None) else 0
    if args.command == "import":
        return _command_import(args)
    if args.command == "diff":
        return _command_diff(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
