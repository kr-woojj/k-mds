# imo-compendium-mapping-validator

IMO Compendium Registry 를 immutable snapshot 으로 적재하고, 외부 데이터 요소를
Registry 항목에 매핑·검증하는 Skill 모듈. FastAPI 기반 API 와 CLI 를 제공한다.

## 구성

| 경로 | 역할 |
|---|---|
| `app/registry/` | 공식 export 적재(import)·버전 비교(diff)·검증 |
| `app/mapping/` | 정규화 → 후보 검색 → 순위화 → 재순위 → 판정 파이프라인 |
| `app/skill/` | Skill 인터페이스(추출기·툴킷·서비스) |
| `app/api/` | FastAPI 라우터, OpenAPI 3.1 문서, 결과 저장소 |
| `migrations/` | SQLite 스키마 마이그레이션 (`NNNN_*.sql`, 자동 적용) |
| `schemas/` | 요청·응답·검증 보고서 JSON Schema |
| `docs/` | 요구사항, 아키텍처, 위협 모델, OpenAPI 산출물 |
| `tests/` | pytest (fixtures 포함) |

## 실행

Python 3.12 이상, [uv](https://docs.astral.sh/uv/) 사용.

```bash
uv sync                      # .venv 생성 및 의존성 설치 (dev 포함)
uv run pytest -q             # 테스트
```

Registry 적재·비교:

```bash
uv run python -m app.registry import --file <export.csv|xlsx> --version <V> [--db registry.sqlite3] [--dry-run]
uv run python -m app.registry diff   --from <V1> --to <V2> [--db registry.sqlite3] [--json]
```

API 서버:

```bash
uv run python -m app.api serve --db registry.sqlite3 --port 8000
```

환경변수 `IMO_API_KEY` 를 설정하면 모든 `/api/v1` 요청에 같은 값의
`X-API-Key` 헤더가 필요하다. OpenAPI 문서는 `/openapi.json` 에서 제공되며,
아래 명령으로 `docs/openapi.json` 을 갱신한다.

```bash
uv run python -m app.api export-openapi --out docs/openapi.json
```

## 규칙

- 마이그레이션은 구조 추가만 허용한다. 적재된 snapshot 데이터의 UPDATE·DELETE 는 금지한다. (`migrations/README.md`)
- `docs/openapi.json` 은 생성물이지만 API 계약 문서로서 추적한다. API 변경 시 함께 갱신한다.
