# kr-ghg-ai-agent

K-MDS IDS Consumer 로 받은 보고 데이터를 IMO Compendium(FAL50) 데이터 요소로 매핑·검증하고, 검증 시스템 전달용 구조로 변환하는 PoC 서비스다.
매핑과 판정은 결정론 규칙과 검증 도구가 한다. LLM 은 풀리지 않은 항목의 후보 제안에만 쓰이며 최종 판정 권한이 없다.

사용 방법은 [USER_GUIDE.md](USER_GUIDE.md), PoC 실증 수행 지시문은 [UserManual.md](UserManual.md)에 있다.

## 처리 흐름

```text
POST /api/v1/ids/events
  → 수신(본문 분류, 전송 정보 분리, SHA-256)
  → 제공자 형식 정규화(코드북)
  → 판별 → 매핑 → 검증 → 변환 → 전달   (상태 전이는 ALLOWED_TRANSITIONS 로 강제)
  → 증적 evidence/{correlation_id}/
```

| 단계 | 소스 | 실패 시 |
| --- | --- | --- |
| 수신 | `adapters/ids_adapter.py` | 알 수 없는 본문은 422 / REVIEW_REQUIRED |
| 제공자 정규화 | `adapters/lab021_ingress.py` | 후보를 좁히지 못하면 원래 이름을 남긴다 |
| 판별·정규화 | `domain/profiling.py`, `domain/normalization.py` | 신뢰도가 낮으면 UNKNOWN |
| 매핑 | `domain/mapping.py` | 검증 도구 장애 시 LLM 단독 진행 금지 |
| 검증 | `domain/validation.py`, `adapters/skill_adapter.py` | FAIL·NOT_VERIFIED 는 성공이 아니다 |
| 변환·전달 | `adapters/kr_gears.py` | 계약이 잠정(PROVISIONAL)이라 실제 전달은 차단 |
| 흐름 제어 | `agents/orchestrator.py` | 같은 `correlation_id` 는 409 |
| 증적 | `evidence.py` | 덮어쓰기 금지, 파일 해시 기록 |

## 매핑 순서

1. 명시된 IMO 번호(존재 확인)
2. 이름 정확 일치
3. 정규화한 이름 일치
4. 별칭(`src/ghg_agent/reference/aliases.json`)
5. 검증 도구의 후보 조회
6. LLM 후보 제안(앞 단계에서 풀리지 않은 항목만)
7. 검증 도구의 매핑 검증과 참조 존재 확인

1~4 단계에서 풀린 필드에는 LLM 을 호출하지 않는다. LLM 후보는 단일 승자이고, 검증을 통과하고, 점수 0.90 이상이며 2위와 0.05 이상 차이 날 때만 받아들인다.

LLM 에는 필드명, 설명, 자료형·단위, 후보 요약만 보낸다. 원본 값, 항차, 선박 식별 정보는 보내지 않는다.

## 설치와 실행

전제: 형제 폴더 `../imo-compendium-mapping-validator` 와 저장소 루트의 `data/raw/FAL50/IMO Compendium.xlsx`.

```bash
uv sync --python 3.12
uv run python tools/prepare_registry.py     # 참조 registry 생성(var/registry.sqlite3)
PYTHONPATH=src uv run uvicorn --factory ghg_agent.api.app:create_app --port 8000
```

Docker 로는 저장소 루트에서 `verification/automation/compose.yaml` 을 쓴다.

| 엔드포인트 | 용도 |
| --- | --- |
| `POST /api/v1/ids/events` | 수신부터 증적까지 한 번에 처리 |
| `POST /api/v1/map`, `/validate`, `/transform/kr-gears` | 단계별 호출 |
| `GET /api/v1/runs/{correlation_id}` | 실행 결과 조회 |
| `GET /api/v1/governance` | 후보 집합·참조 모델 승인 상태 |
| `GET /health`, `GET /ready` | 상태 확인(READY / DEGRADED / NOT_READY) |

환경변수는 저장소 루트 `.env.example` 에 설명이 있다. 기본은 `LLM_PROVIDER=mock` 이고, 실제 모델은 `ALLOW_LIVE_LLM=true` 일 때만 호출한다.

## 시험

```bash
uv run pytest tests/unit tests/contract -q     # 47건
uv run pytest tests/integration -q             # registry 준비 후
uv run python tools/run_mock_e2e.py            # 모의 종단 시험 8개 시나리오
uv run ruff check src tools tests && uv run mypy src
```

## 증적

`evidence/{correlation_id}/` 에 `manifest.json`(실행 식별자, 코드 커밋, 실제/모의 구분, 파일 해시)과 단계별 결과(`raw-input.json`, `normalized-input.json`, `mapping-result.json`, `validation-result.json`, `llm-calls.json`, `skill-calls.json`, `kr-gears-output.json`, `summary.md` 등)가 남는다.
무결성은 `ghg_agent.evidence.verify_evidence` 로 검사한다.

## 검증 도구와 MCP

- 검증 도구는 Python import 로 호출한다(`adapters/skill_adapter.py` → validator 의 `MappingToolkit`). HTTP 래퍼는 없다.
- MCP 는 선택 경로다. 서버 `tools/mcp_server.py`(FastMCP, stdio)는 도구 이름을 검증 도구에서 런타임에 읽어 등록하고, 클라이언트는 `adapters/mcp_adapter.py` 다.

## 제한 사항

- 검증 시스템(KR GEARs)의 제출 계약이 확인되지 않아 변환 결과는 PROVISIONAL 이고 실제 전달은 mock 뿐이다. 최종 상태는 `REVIEW_REQUIRED` 가 기본이다.
- 단위 변환을 하지 않는다.
- FAL50 원본의 불일치(IMO0654 형식 `n..10` 과 코드 목록의 문자열 값)는 실패로 처리한다.
- FAL50 에 벙커링 이벤트 코드가 없어 해당 이벤트는 기타 이벤트로 다룬다.
- 프롬프트 주입 방어는 구분자와 후보 제한 방식이다. LLM 응답은 검증을 통과해야 하지만 구분자 우회 자체를 막지는 못한다.
- 전체 목록은 `reports/known-limitations.json`.

## 문제 해결

| 증상 | 조치 |
| --- | --- |
| `REGISTRY_DB_NOT_FOUND` | `uv run python tools/prepare_registry.py` 를 먼저 실행한다 |
| `/ready` 가 NOT_READY | `IMO_MAPPING_SKILL_PATH` 와 registry 경로를 확인한다 |
| 409 `DUPLICATE_CORRELATION_ID` | 같은 식별자의 증적이 이미 있다. 새 식별자를 쓴다 |
| 실제 모델 호출 실패 | `ALLOW_LIVE_LLM=true` 와 `LLM_ENDPOINT` 설정을 확인한다 |
