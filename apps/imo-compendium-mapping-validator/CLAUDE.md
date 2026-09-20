# imo-compendium-mapping-validator

- 설치·테스트: `uv sync` / `uv run pytest -q` (71건). API: `uv run python -m app.api serve --db registry.sqlite3 --port 8000`
- 마이그레이션은 구조 추가만. 적재된 snapshot 의 UPDATE·DELETE 금지 (`migrations/README.md`).
- `docs/openapi.json` 은 생성물이지만 API 계약으로 추적한다. API 변경 시 `export-openapi` 로 갱신.
- `apps/kr-ghg-ai-agent` 가 이 폴더를 Python import 로 호출한다(형제 폴더 기본 경로). 폴더 이름을 바꾸지 않는다.
