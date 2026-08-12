# schemas/ Local AGENTS.md

Root `AGENTS.md`가 Master Contract이다. 이 문서는 `schemas/` 폴더의 추가 제약만 정의한다.

## 책임

- `source/`: Pydantic 원천 모델 (`canonical_model.py`, `mapping_model.py`, `validation_model.py`)
- `generated/`: Pydantic에서 생성한 JSON Schema와 OpenAPI (직접 수정 금지, `DO_NOT_EDIT.md` 참조)

생성 흐름: Pydantic Source → JSON Schema → OpenAPI → MCP Input/Output Contract (AGENTS.md §4.6)

## 추가 금지사항

- `generated/`의 JSON Schema 또는 OpenAPI 직접 수정 — 수정은 Pydantic Source 변경 후 재생성으로만
- Pydantic 외의 원천(수기 JSON Schema 등)으로 Contract 정의
- PASS, WARNING, FAIL 상태 불변조건을 `model_validator` 없이 문서로만 정의
- Contract(입출력 구조) 변경 시 실패하는 Contract Test 선행 없이 모델 수정 (TDD, AGENTS.md §15.7)
- Schema에 검증되지 않은 IMO ID, Format 또는 Code Value를 기본값·예시로 포함
