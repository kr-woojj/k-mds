# src/ Local AGENTS.md

Root `AGENTS.md`가 Master Contract이다. 이 문서는 `src/` 폴더의 추가 제약만 정의한다.

## 책임

Python Package Root는 `src/k_mds`이다.

- `models/`: 핵심 객체 및 타입
- `services/`: 검색, 매핑, 검증 Application Service
- `skills/`: Agent가 호출하는 결정론적 Skill
- `langgraph/`: State, Node, Router, Workflow
- `mcp/`: Resource, Tool, Prompt, Server
- `adapters/`: KR GEARs, IDS, LLM 외부 연계

## 추가 금지사항 (의존성 경계, AGENTS.md §9)

- MCP Tool → LangGraph Node 또는 LangGraph Node → MCP Tool 의존
- Skill, MCP Resource, LangGraph Node에서 원본 Excel 또는 HTML 직접 조회 (정규화 Snapshot만 조회)
- MCP Tool에 Application Service 업무 로직 중복 구현
- Core Service가 KR GEARs API Schema에 직접 의존 (Target 전용 로직은 `adapters/`에만)
- LLM 호출로 PASS, WARNING, FAIL 최종 결정 — 상태 결정은 결정론적 Rule Engine만 수행
- 검증 노드에서 LLM 호출
- FAIL 상태에서 Transform 또는 Submit 진행
- 실제 온실가스 검증 시스템(KR GEARs) 운영계 제출 기능 구현 또는 활성화 (Dry-run까지만)
- 동작 추가·변경 시 실패하는 Unit/Contract/Routing Test 선행 없이 구현 (TDD, AGENTS.md §15.7)
- 결과에 FAL Version, Ontology Version, Profile Version, Rule ID, Evidence 누락
