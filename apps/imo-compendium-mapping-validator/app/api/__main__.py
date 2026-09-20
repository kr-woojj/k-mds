"""API 유틸 CLI.

사용:
  python -m app.api export-openapi --out docs/openapi.json [--db PATH]
  python -m app.api serve [--db PATH] [--host H] [--port P]
    API Key 인증은 환경변수 IMO_API_KEY 로 켠다 (미설정 시 인증 없음).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from app.api import create_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.api")
    subparsers = parser.add_subparsers(dest="command", required=True)
    export = subparsers.add_parser(
        "export-openapi", help="OpenAPI 3.1 문서를 파일로 내보낸다"
    )
    export.add_argument("--out", type=Path, required=True)
    export.add_argument("--db", type=Path, default=None)
    serve = subparsers.add_parser("serve", help="API 서버를 실행한다")
    serve.add_argument("--db", type=Path, default=Path("registry.sqlite3"))
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    if args.command == "serve":
        import uvicorn

        app = create_app(args.db, api_key=os.environ.get("IMO_API_KEY") or None)
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    if args.command == "export-openapi":
        if args.db is not None:
            db_path = args.db
        else:
            db_path = Path(tempfile.mkdtemp(prefix="openapi-export-")) / "schema.sqlite3"
        app = create_app(db_path)
        document = app.openapi()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"openapiVersion={document.get('openapi')}")
        print(f"pathCount={len(document.get('paths', {}))}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
