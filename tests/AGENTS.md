# tests/ Local AGENTS.md

Root `AGENTS.md`가 Master Contract이다. 이 문서는 `tests/` 폴더의 추가 제약만 정의한다.

## 책임

- `unit/`: 함수와 Skill 테스트
- `integration/`: LangGraph, MCP 및 Repository 연계 테스트
- `contracts/`: MCP와 OpenAPI 입출력 계약 테스트
- `fixtures/`: 정상(PASS), 경고(WARNING), 실패(FAIL) 데이터

## 추가 금지사항

- Fixture에 공식 출처에서 확인되지 않은 IMO ID, Technical Position, Format, Code Value를 실제 값처럼 기재 — 테스트용 가상 값은 가상임이 드러나는 형태로 작성
- Fixture에 실제 선박·운항 데이터, 개인정보, 기밀정보 또는 Credential 저장
- 테스트 실패를 만들기 위해 기존 정상 Test, Fixture 또는 Production Code를 의도적으로 훼손
- 검증 동작 테스트에서 PASS, WARNING, FAIL 세 상태 중 일부만 커버 (세 상태와 상태 불변조건을 모두 검증)
- 테스트에서 `data/raw/`의 공식 원본(Excel, HTML, PDF) 직접 파싱 (정규화 Snapshot 또는 Fixture만 사용) — 단, `source-manifest.yaml` 등 Repository가 관리하는 Metadata의 구조 검증은 허용
- 외부 시스템(KR GEARs 등) 실제 API 호출 — 외부 연계는 Mock 또는 Dry-run Contract로만 테스트
