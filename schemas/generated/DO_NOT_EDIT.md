# 직접 수정 금지

이 폴더(`schemas/generated/`)의 JSON Schema와 OpenAPI 파일은 `scripts/generate_schemas.py`가 `schemas/source/`의 Pydantic 원천 모델에서 생성한다 (AGENTS.md §2.5, §4.6).

- 이 폴더의 파일을 직접 수정하지 않는다.
- 수정이 필요하면 Pydantic Source Model 또는 생성 스크립트를 수정한 후 `make build`를 실행한다.
- 현재는 Bootstrap 단계로 생성 파이프라인이 아직 구현되지 않았다.
