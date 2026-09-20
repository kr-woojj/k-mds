# kr-ghg-ai-agent

GHG AI Agent PoC — K-MDS IDS Consumer 입력을 받아 IMO Compendium(FAL50) 기반
결정론 매핑·검증을 수행하고 KR GEARs 변환(PROVISIONAL)까지 이어지는
Multi-Agent 파이프라인. 재현 가능한 Evidence 생성과 Fail-Closed 동작을
최우선으로 한다.

## 1. Purpose and Scope

- K-MDS IDS Consumer → GHG AI Agent → IMO mapping 후보 생성
  → `imo-compendium-mapping-validator` Skill 검증 → deterministic validation
  → KR GEARs 변환 → mock delivery → Evidence
- LLM 은 semantic mapping **후보 생성**과 설명 생성에만 사용된다.
  최종 판정 권한이 없다 (LLM Is Not a Source of Truth).

## 2. Repository Boundaries

| 경로 | 역할 | 쓰기 |
|---|---|---|
| `k-mds/` (상위 2단계) | 통합 저장소 루트. FAL50 원본 xlsx (`data/raw/FAL50/IMO Compendium.xlsx`), 표준 모델 (`shared/standard-model/`) | read-only |
| `kr-ghg-ai-agent/` (본 repo) | PoC 구현 | 대상 |
| `../imo-compendium-mapping-validator/` | 기존 Skill — Python import 로 호출 (형제 폴더) | read-only |
| `kr-ai-agents/` | 패턴 참조 (LangGraph/MCP/LLM) | read-only |
| `../data-space/` | Noon Report(PerformanceReport) 구현. OpenAPI 는 `shared/standard-model/openapi.yaml` | read-only |

## 3. Architecture

```
POST /api/v1/ids/events
  └─ IngressAgent (ids_adapter): body 분류(RAW_JSON_BODY/FILE_REFERENCE/UNKNOWN),
     transport/business 분리, SHA-256, raw Evidence
  └─ LangGraph StateGraph (agents/orchestrator.py, PipelineState[Pydantic])
       profile → map → validate → transform → deliver
       상태 전이는 ALLOWED_TRANSITIONS 로 강제
  └─ EvidenceWriter: evidence/{correlation_id}/ (덮어쓰기 금지, manifest+해시)
```

## 4. Agent Responsibilities

| Agent | 책임 | 실패 정책 |
|---|---|---|
| OrchestratorAgent | 상태 전이, idempotency(중복 correlation_id 409), Evidence 완결 | 잘못된 전이 즉시 실패 |
| IngressAgent | body 분류, correlation_id, 해시, transport 분리 | UNKNOWN → 422/REVIEW_REQUIRED |
| DataProfilerAgent | VESSEL_PERFORMANCE/NOON_REPORT/EVENT_REPORT/UNKNOWN + 정규화 | 저신뢰/경쟁 → UNKNOWN |
| IMOMapperAgent | 결정론 우선 매핑 (C-7 순서), LLM 후보는 검증 후에만 승격 | Skill 장애 시 LLM 단독 진행 금지 |
| MappingValidationAgent | Skill validate_mapping + code list + 정책 검증 | FAIL/NOT_VERIFIED 는 성공 아님 |
| KRGearsTransformationAgent | Noon/Event/Perf 분리 변환, provenance 유지 | PROVISIONAL → 실delivery 차단 |
| EvidenceAgent | manifest, file 해시, real/mock 구분 기록 | stage output 덮어쓰기 금지 |

## 5. Data Flow

fixture/IDS body → IngressResult(+business payload) → ProfileResult
→ `CanonicalField[]` → `MappingResult`(method/confidence/candidate_list)
→ `ValidationResult`(PASS/WARNING/FAIL/NOT_APPLICABLE/NOT_VERIFIED)
→ `TransformResult`(payload PROVISIONAL + 실계약 KrGearsReport verdict)
→ `DeliveryResult`(mock) → Evidence 패키지

## 6. Deterministic-First Mapping Policy

순서: ① explicit IMO id(존재 검증) ② exact name ③ normalized name
④ 구성 alias(`src/ghg_agent/reference/aliases.json`) ⑤ Skill map/list_candidates
⑥ LLM 후보 생성(미해결 시에만) ⑦ Skill validate_mapping ⑧ reference 존재 검증.
①~④ 로 해결된 필드에는 LLM 이 호출되지 않는다
(테스트: `tests/unit/test_mapper.py::test_exact_fields_never_call_llm`).
LLM 후보 승격 조건: 단일 승자 + validator PASS/WARNING + score ≥ 0.90 + gap ≥ 0.05.

## 7. Skill Invocation Method

Python import 어댑터 (`adapters/skill_adapter.py`):
validator 의 `app.skill.MappingToolkit` (`list_tools`/`invoke`) 를 그대로 호출
(validator 자체 테스트와 동일한 사용법). registry 는 validator 공식 CLI
`python -m app.registry import` 로 적재한다. HTTP wrapper 를 만들지 않았다.

## 8. MCP Invocation Method

- Server: `tools/mcp_server.py` — FastMCP(stdio). tool 이름은 toolkit
  `list_tools()` 에서 **런타임 발견**해 등록 (발명 없음).
- Client: `adapters/mcp_adapter.py` — `MultiServerMCPClient` + `get_tools()`
  (kr-ai-agents 실코드 패턴). 모든 호출 audit (server/transport/tool/latency/
  sanitized args/real-mock).
- MCP 는 optional 경로: authoritative lookup 은 Python import Skill 이 담당.

## 9. LLM Data Minimization Policy

외부 LLM 에는 다음만 전달: 필드명(≤120자), sanitize 된 설명(≤300자),
declared type/unit, report context 문자열, registry 후보 요약(번호+이름 ≤10개).
전체 payload/항차/선박식별정보/원본값/비밀은 전달하지 않는다.
원천 텍스트는 `<data>` delimiter 안에 두고 지시문 해석을 금지한다 (S-4).

## 10. Setup

```bash
cd kr-ghg-ai-agent
uv sync --python 3.12
uv run python tools/prepare_registry.py   # FAL50 xlsx → derived CSV → validator CLI 적재
```

전제: 형제 디렉터리에 `imo-compendium-mapping-validator/`(uv 환경 포함)와
k-mds 루트에 `data/raw/FAL50/IMO Compendium.xlsx` 존재.

## 11. Mock Execution

```bash
uv run python tools/run_mock_e2e.py       # 8개 시나리오, evidence/ 생성, 무결성 검증
```

## 12. Live LLM Execution

```bash
ALLOW_LIVE_LLM=true LIVE_LLM_ENV_FILE=<credential .env 경로> \
  uv run pytest tests/integration/test_live_llm.py -m live_llm
```

credential 없으면 `SKIPPED_CREDENTIAL_NOT_AVAILABLE` 로 skip 되며 성공으로
보고되지 않는다. Evidence 는 `evidence/live-llm/` 에 redacted 로 저장된다.

## 13. API Execution

```bash
PYTHONPATH=src uv run uvicorn --factory ghg_agent.api.app:create_app --port 8000
# 또는: docker compose up --build  (참고: 본 PoC 검증 시점에는 Docker daemon
#   미기동으로 이미지 빌드가 확인되지 않았다 — 로컬 러너는 검증됨)
```

Endpoints: `POST /api/v1/ids/events`, `POST /api/v1/map`, `POST /api/v1/validate`,
`POST /api/v1/transform/kr-gears`, `GET /api/v1/runs/{correlation_id}`,
`GET /health`, `GET /ready` (READY/DEGRADED/NOT_READY).

## 14. Test Commands

```bash
uv run pytest                      # unit + contract + integration (live_llm 은 조건부)
uv run pytest tests/unit -q
uv run pytest tests/contract -q
uv run pytest tests/integration -q
uv run ruff check src tools tests
uv run mypy src
```

## 15. Evidence Structure

`evidence/{correlation_id}/`: `manifest.json`(run_id, code_commit,
synthetic_data, real/mock 플래그, file_hashes), `raw-input.json`,
`raw-input.sha256`, `ingress-result.json`, `profile-result.json`,
`normalized-input.json`, `agent-trace.json`, `skill-calls.json`,
`mcp-calls.json`, `llm-calls.json`, `mapping-result.json`,
`validation-result.json`, `kr-gears-output.json`(도달 시),
`delivery-result.json`(도달 시), `summary.md`.
무결성 검증: `ghg_agent.evidence.verify_evidence`.

## 16. Real vs Mock Integration Matrix

| 구성 | Skill | LLM | MCP | KR GEARs delivery | 위치 |
|---|---|---|---|---|---|
| 기본 E2E | real | mock | off | mock | tests/integration/test_e2e_pipeline.py |
| API E2E | real | mock | off | mock | tests/integration/test_api.py |
| 결정론 전용(LLM 금지) | real | 금지(ForbiddenLLM) | off | - | tests/unit/test_mapper.py |
| Real MCP | real(stdio 경유) | - | real stdio | - | tests/integration/test_mcp_real.py |
| Live LLM | real | real(azure_openai) | off | - | tests/integration/test_live_llm.py |

## 17. KR GEARs Contract Status

**PARTIAL.** 확인된 실계약은 validator 의 `KrGearsReport`(검증 결과 전달
envelope, `imo-compendium-mapping-validator/app/api/schemas.py` +
`docs/openapi.json`) 뿐이며, 본 PoC 는 verdict report 를 그 Pydantic 모델로
실제 검증한다. KR GEARs **제출 스키마/필드 사전/endpoint 는 미발견** —
변환 payload 는 `contract_status: PROVISIONAL`, 실제 delivery 는 차단(mock 만),
최종 상태는 `REVIEW_REQUIRED`. 실계약 확보 전에는 연동 성공을 선언하지 않는다.

## 18. Security Limitations

- 비밀 값은 코드/fixture/Evidence/로그에 기록하지 않는다 (redaction 정책).
- 참조 repo 들(`kr-ai-agents`, `data-space`)에 실값 `.env` 가 존재한다 —
  본 PoC 범위 밖이지만 회전/보호 조치가 필요하다 (governance §10.5 R-3 참조).
- prompt injection 방어는 delimiter + 후보 제한 방식이다. LLM 응답은 어차피
  validator 를 통과해야 하므로 fail-closed 이지만, delimiter 우회 자체를
  막지는 못한다.

## 19. Known Limitations

`reports/known-limitations.json` 참조. 요약:
- K-MDS IDS envelope 미확인 → RAW_JSON_BODY/UNKNOWN 만 구분 (KNOWN_ENVELOPE 없음)
- KR GEARs 제출 계약 미확인 → PROVISIONAL
- FAL50 원본 내부 불일치: IMO0654 format `n..10` vs code list 값 `HFO` 등 문자열
  → fail-closed (DATATYPE_HARD_CONFLICT)
- FAL50 에 BUNKERING event code 부재 → 해당 이벤트는 REVIEW_REQUIRED
- 단위 변환 미수행 (canonical unit 권위 근거 미확인, conversion_applied=false)
- registry 적재 시 IMO0629 business rule 을 합집합으로 통일 (DR-2,
  `var/registry/derivation-manifest.json` 에 기록)

## 20. Troubleshooting

- `REGISTRY_DB_NOT_FOUND`: `uv run python tools/prepare_registry.py` 먼저 실행.
- `/ready` NOT_READY: `IMO_MAPPING_SKILL_PATH` 와 registry DB 경로 확인.
- 409 DUPLICATE_CORRELATION_ID: 동일 correlation_id Evidence 존재 —
  새 id 를 쓰거나 evidence 디렉터리를 정리(감사 목적상 삭제는 신중히).
- live LLM 실패: `ALLOW_LIVE_LLM=true` 및 provider env 존재 여부 확인
  (값은 로그에 출력되지 않는다).
