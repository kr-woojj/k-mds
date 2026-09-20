# data-space (Ship-ODMS)

- 원본 저장소 kr-woojj/data-space 의 Copilot 워크숍 자료(README, docs/custom-instructions, complete/)는 통합 시 제외했다. 앱 구현(python/, java/, dotnet/, javascript/)만 있다.
- OpenAPI 명세와 ER 모델은 `../../shared/standard-model/` 이 원본이다. `python/main.py` 의 `OPENAPI_PATH` 가 그곳을 가리킨다. 앱 안에 사본을 두지 않는다.
- Python: `cd python && uv sync && uv run uvicorn main:app`. 테스트 없음. `ship_odms.db` 는 실행 산출물(git 제외).
- `.env` 는 원본 폴더에 남아 있다.
