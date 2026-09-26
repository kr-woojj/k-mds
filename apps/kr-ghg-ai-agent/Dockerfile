# kr-ghg-ai-agent — FastAPI service
# 주의: validator Skill 은 Python import 로 호출되므로 컨테이너에
# imo-compendium-mapping-validator 소스와 준비된 registry DB 가 필요하다.
# compose 파일이 두 경로를 read-only 로 mount 한다.
FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src ./src
COPY tools ./tools
COPY tests/fixtures ./tests/fixtures

ENV PYTHONPATH=/app/src
EXPOSE 8000
# 빌드 시 동기화된 venv 를 직접 실행한다 — `uv run` 은 기동 때마다 dev 그룹을 재동기화(네트워크 필요)하므로 오프라인 설치처(RIMS)에서 실패한다.
CMD ["/app/.venv/bin/uvicorn", "--factory", "ghg_agent.api.app:create_app", "--host", "0.0.0.0", "--port", "8000"]
