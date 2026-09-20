# imo-compendium-mapping-validator 아키텍처

> 문서 버전: 0.1.0 (Draft) — 코드 작성 전 설계
> 요구사항 추적: `docs/requirements.md`의 REQ-### 참조

## 1. 설계 원칙

1. **Registry가 진실의 원천** — IMO Data Number는 Registry 조회 결과로만
   존재한다 (REQ-006, REQ-007).
2. **LLM은 보조** — 결정론 후보 집합 안에서의 재순위화와 설명만 담당하고,
   상태 결정·검증·코드 산출에 관여하지 않는다 (REQ-014).
3. **Fail-closed** — 불확실하면 MATCHED가 아니라 REVIEW_REQUIRED /
   NO_MATCH / FAIL이다 (REQ-015, REQ-033).
4. **모든 결과는 근거를 갖는다** — compendiumVersion + registryRecordRef +
   inputHash 없는 결과는 반환되지 않는다 (REQ-004, REQ-008, REQ-009).

## 2. 컴포넌트 구성

```text
imo_compendium_mapping_validator/
├── api/                  # FastAPI Router, OpenAPI 3.1 (REQ-029)
│   ├── mapping.py        #   POST /v1/mappings
│   ├── validation.py     #   POST /v1/validations
│   └── registry.py       #   GET  /v1/registry/versions, /records/{id}
├── contracts/            # Pydantic v2 모델 = 단일 원천 (REQ-031)
│   ├── request.py        #   MappingRequest (mapping-request.schema.json)
│   ├── response.py       #   MappingResponse (mapping-response.schema.json)
│   └── report.py         #   ValidationReport (validation-report.schema.json)
├── ingest/               # 입력 정규화 (REQ-001, REQ-003)
│   ├── json_source.py
│   ├── json_schema_source.py
│   ├── csv_columns_source.py
│   └── api_sample_source.py
├── registry/             # Registry 적재·조회 (REQ-006, REQ-008, REQ-010)
│   ├── loader.py         #   Compendium snapshot -> SQLite (hash 검증)
│   ├── models.py         #   SQLAlchemy ORM
│   └── repository.py     #   읽기 전용 조회 API
├── matching/
│   ├── normalizer.py     #   필드명 정규화 (결정론)
│   ├── exact.py          #   Exact Match (REQ-012)
│   ├── search.py         #   후보 검색 top-N (REQ-013)
│   ├── scorer.py         #   결정론 confidence 합성 (REQ-015)
│   ├── reranker.py       #   LLM 재순위화 boundary (REQ-014, REQ-016)
│   └── gate.py           #   Registry 존재 재검증 출력 게이트 (REQ-007)
├── validation/           # 전부 deterministic (REQ-018~REQ-023)
│   ├── type_check.py
│   ├── format_check.py
│   ├── unit_check.py
│   ├── codelist_check.py
│   └── refmodel_check.py
├── namespaces/           # imo / xmo 분리 (REQ-011)
├── audit/                # append-only audit log (REQ-026)
└── config.py             # 임계값·제한 설정 (REQ-005, REQ-015)

tests/
├── fixtures/             # 샘플 IMO 값의 유일한 위치 (REQ-028)
├── unit/  contracts/  integration/
```

## 3. 데이터 흐름

```text
[입력: JSON | JSON Schema | CSV 컬럼 | API 샘플]
        │  (1) 계약 검증 REQ-002, inputHash 계산 REQ-004
        ▼
[Ingest: 필드 추출·정규화]  ── 원본 불변 REQ-003, normalizedInput REQ-027
        ▼
[Exact Match]  ──일치──▶ MATCHED (confidence=1.0, LLM 미사용) REQ-012
        │ 불일치
        ▼
[Deterministic Search: top-N Registry 후보] REQ-013
        │  후보 0개 ─▶ NO_MATCH
        ▼
[결정론 Scorer: base confidence] REQ-015
        ▼
[LLM Re-ranker (선택 경로)] REQ-014
   · 입력: 후보 record 요약 + 정규화 필드 문맥
   · 출력: 후보 id 순열 + 설명 (구조 파싱, 집합 밖 id 폐기)
   · 실패 시: base 점수 유지, exact 아님 → REVIEW_REQUIRED 이하 REQ-016
        ▼
[상태 결정 (결정론)] REQ-015
   confidence ≥ 0.90 & 단독 우세 → MATCHED
   ≥ 0.40                        → REVIEW_REQUIRED(후보 포함)
   그 외                          → NO_MATCH
        ▼
[Registry 존재 재검증 게이트] REQ-007 ── 위반 → 제거 + audit
        ▼
[Validation (요청 시): 타입/형식/단위/코드/문맥] REQ-018~REQ-023
        ▼
[응답 조립: compendiumVersion + registryRecordRef + inputHash]
        ▼                                   REQ-008, REQ-009, REQ-025
[Audit Log 기록] REQ-026
```

## 4. Registry 스키마 (SQLite / SQLAlchemy)

| 테이블 | 주요 컬럼 | 비고 |
|---|---|---|
| `compendium_version` | version(PK), source_hash, record_count, loaded_flag | 스냅샷 단위 REQ-008 |
| `data_element` | id(PK), version(FK), imo_data_number(UNIQUE per version), name, definition, value_type, format_spec | REQ-006 |
| `dataset` | id, version, dataset_key, label, status | |
| `dataset_membership` | dataset_id, element_id, marker | |
| `refmodel_occurrence` | id, element_id, path, level, kind_of_object | REQ-022 |
| `code_list` / `code_list_value` | id, element 참조, value, version | REQ-021 |
| `business_rule` | id, element 참조, rule_key | |
| `alias` | element_id, normalized_alias, origin | exact match 보조 REQ-012 |
| `approved_mapping` | source_signature, element_id, approved_by_role, evidence_ref | REQ-017 |
| `xmo_code` | xmo_id(PK, `^XMO[0-9A-Z-]+$`), label, owner_role | IMO와 join 금지 REQ-011 |
| `audit_event` | seq(PK autoincr), event_type, input_hash, version, correlation_id, payload_digest | append-only REQ-026 |

적재 규칙: loader만 쓰기 가능, 서비스 경로는 read-only 연결 사용
(REQ-010). Registry 파일 hash 불일치 시 적재 거부.

## 5. LLM Boundary 상세 (REQ-014)

- 호출 입력: 후보 목록 `[ {candidateId, name, definition 요약, dataset 문맥} ]`
  + 정규화 필드 정보. **후보 목록 밖 정보로 코드를 만들 수 없는 구조.**
- 호출 출력 계약: `{"ranking": [candidateId...], "rationale": str}` —
  JSON 파싱 실패, 미지 id, 중복 id는 전량 폐기하고 base 순위 사용.
- rationale은 응답의 `explanation` 필드로만 전달되며 판정에 미사용.
- 모델·프롬프트 버전은 audit event에 기록 (REQ-026).
- 오프라인/테스트 환경은 mock reranker 주입 (REQ-034).

## 6. 상태 모델

매핑: `MATCHED` | `REVIEW_REQUIRED` | `NO_MATCH`
검증: Finding severity `ERROR|WARNING|INFO` → 종합 `PASS|WARNING|FAIL`
(REQ-015, REQ-023). 두 축은 독립 필드로 반환하며 혼합하지 않는다.

## 7. API (FastAPI, OpenAPI 3.1)

| Method | Path | 설명 |
|---|---|---|
| POST | `/v1/mappings` | 필드 집합 매핑. Body=mapping-request, 200=mapping-response |
| POST | `/v1/validations` | 매핑 확정본 + 샘플 값 검증. 200=validation-report |
| GET | `/v1/registry/versions` | 적재된 Compendium version 목록 |
| GET | `/v1/registry/elements/{imoDataNumber}` | 근거 record 조회 (존재 시에만) |

- 모든 응답에 `compendiumVersion`, `inputHash`(POST), `auditRef` 포함.
- OpenAPI 문서는 Pydantic 모델에서 생성 (REQ-031).

## 8. 결정론·재현성 (REQ-030)

- 정규화·검색·점수·검증은 순수 함수로 구현, 사전/인덱스는 version 고정.
- 결과 본문에 timestamp/uuid/random 금지. correlation id는 헤더와
  audit에만 존재.
- LLM 경로는 결과의 `rerankedByLlm: true` 플래그로 표시하여 재현성
  경계를 명시한다.

## 9. 미결정 사항 (구현 단계 결정)

- 후보 검색 인덱스: SQLite FTS5 vs 사전 기반 토큰 인덱스 (성능 REQ-032)
- 승인 매핑 워크플로 UI/CLI 범위 (REQ-017)
- 단위 환산 규칙 테이블의 관리 주체 (REQ-020)
