"""FastAPI 애플리케이션 팩토리.

- OpenAPI 3.1 문서는 /openapi.json 에서 제공되며,
  `python -m app.api export-openapi --out docs/openapi.json`으로 내보낼 수 있다.
- api_key가 설정되면 모든 /api/v1 요청에 X-API-Key가 필요하다 (SEC-001).
- POST 요청은 X-Payload-SHA256 헤더로 무결성을 선택 검증한다 (SEC-002).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.errors import ApiError
from app.api.routes import router
from app.registry.database import init_db, make_session_factory
from app.skill.service import MappingSkillService

API_DESCRIPTION = (
    "IMO Compendium Registry 기반 필드 매핑·검증 API. "
    "모든 IMO Data Number는 Registry에 존재하는 값만 반환되며, 결과에는 "
    "compendium version과 근거 record가 포함된다. 예시의 'IMOnnnn'은 "
    "자리표시 표기다 — 실제 식별자는 /api/v1/registry/elements 로 조회한다."
)


def create_app(
    db_path: Path,
    *,
    api_key: str | None = None,
    active_version: str | None = None,
    migrations_dir: Path | None = None,
) -> FastAPI:
    engine = init_db(db_path, migrations_dir)
    session_factory = make_session_factory(engine)
    service = MappingSkillService(
        session_factory=session_factory, active_version=active_version
    )

    app = FastAPI(
        title="imo-compendium-mapping-validator",
        version="0.1.0",
        description=API_DESCRIPTION,
        openapi_url="/openapi.json",
    )
    app.state.service = service
    app.state.api_key = api_key
    app.include_router(router)

    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, error: ApiError) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content=error.body())

    return app
