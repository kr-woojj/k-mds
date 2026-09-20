# imo-compendium-mapping-validator 요구사항 명세

> 프로젝트: imo-compendium-mapping-validator
> 문서 버전: 0.1.0 (Draft)
> 상태: 코드 작성 전 설계 단계

이기종 해사 데이터 필드(JSON, JSON Schema, CSV 컬럼 정의, API 샘플)를
IMO Compendium Registry의 공식 IMO Data Number와 매핑하고, 데이터 타입·형식·
단위·코드 목록·Reference Model 문맥을 검증하는 AI Agent Skill의 요구사항을
정의한다.

모든 요구사항은 `REQ-###` ID로 추적하며, `docs/architecture.md`,
`docs/threat-model.md`, `schemas/*.schema.json` 및 향후 테스트 코드에서
이 ID를 참조한다.

우선순위: `MUST`(필수) / `SHOULD`(권장) / `MAY`(선택)

---

## 1. 용어

| 용어 | 정의 |
|---|---|
| Registry | 특정 Compendium version의 IMO Data Number, Data Element, Data Set, Code List, Business Rule, Reference Model 관계를 담은 읽기 전용 로컬 저장소 (SQLite) |
| IMO Data Number | Registry에 존재하는 공식 식별자. Pattern `^IMO[0-9]{4}$` |
| XMO Code | Registry에 없는 사내/임시 코드. IMO namespace와 분리 관리 |
| Mapping | 입력 필드 1개를 IMO Data Number 후보에 연결하는 결정 |
| Validation | 매핑된 필드의 값·타입·형식·단위·코드·문맥 검증 |
| Deterministic Path | LLM을 포함하지 않는 코드 경로. 동일 입력 → 동일 출력 |
| Candidate | Deterministic 검색이 산출한 Registry record 후보 |
| Evidence | 결과의 근거가 된 Registry record 참조 (record id + version) |

---

## 2. 기능 요구사항 — 입력

### REQ-001 (MUST) 다중 입력 형식 수용
시스템은 다음 4가지 입력 형식을 수용해야 한다.
1. JSON 문서 (필드 경로 자동 추출)
2. JSON Schema (draft 2020-12; properties에서 필드 정의 추출)
3. CSV 컬럼 정의 (컬럼명, 타입, 단위, 설명의 표 형식 정의)
4. API 샘플 (요청/응답 예시 JSON + 선택적 필드 설명)

### REQ-002 (MUST) 입력 계약 검증
모든 요청은 `schemas/mapping-request.schema.json`에 대해 검증되어야 하며,
위반 시 매핑을 수행하지 않고 구조화된 오류를 반환한다 (fail-closed).

### REQ-003 (MUST) 원본 불변성
시스템은 입력 원본을 절대 수정하지 않는다. 정규화된 필드 표현은
`normalizedInput`으로 별도 생성하며 원본과 함께 반환하지 않고
audit 저장소에만 원본 hash를 남긴다. (절대 조건 8)

### REQ-004 (MUST) 입력 Hash
모든 요청 입력에 대해 정규화 전 원본 byte 기준 SHA-256 `inputHash`를
계산하여 모든 결과와 audit log에 포함한다. (절대 조건 9)

### REQ-005 (SHOULD) 입력 크기 제한
단일 요청의 필드 수(기본 500)와 payload 크기(기본 5 MB)를 제한하고
초과 시 요청을 거부한다.

---

## 3. 기능 요구사항 — Registry

### REQ-006 (MUST) Registry가 유일한 IMO Code 원천
IMO Data Number, Data Element 정의, Code List, Business Rule,
Reference Model 관계는 Registry에서만 조회한다. LLM 지식, 하드코딩 값,
외부 검색 결과를 IMO Code 원천으로 사용하지 않는다. (절대 조건 1, 2)

### REQ-007 (MUST) IMO Code 생성·추측 금지
어떤 코드 경로도 IMO Data Number를 생성, 보간, 추측하지 않는다.
출력 직전 게이트가 모든 IMO Data Number를 Registry 존재 여부로 재검증하고,
미존재 코드는 결과에서 제거하며 `REGISTRY_GATE_VIOLATION` audit 이벤트를
기록한다. (절대 조건 1, 2)

### REQ-008 (MUST) Compendium Version 고정
Registry는 Compendium version 단위 스냅샷으로 적재된다. 각 요청은 정확히
하나의 version에 대해 처리되고, 모든 결과에 `compendiumVersion`을
포함한다. (절대 조건 3)

### REQ-009 (MUST) 근거 Record 포함
모든 매핑·검증 결과 항목은 근거가 된 Registry record 참조
(`registryRecordRef`: record 종류 + record id + version)를 포함한다.
근거 없는 결과는 반환하지 않는다. (절대 조건 3)

### REQ-010 (MUST) Registry 적재 무결성
Registry 적재는 원본 파일의 SHA-256 검증을 통과해야 하며, 적재 후
Registry는 요청 처리 경로에서 읽기 전용이다. 적재 이력(원본 hash,
version, record 수)은 audit log에 기록한다.

### REQ-011 (MUST) XMO Namespace 분리
사내/임시 코드는 `xmo` namespace 테이블에 저장하고, IMO namespace와
합집합 검색하지 않는다. 응답에서 두 namespace는 항상 명시적으로 구분된
필드로 반환한다. XMO 코드는 `imoDataNumber` 필드에 나타날 수 없다.
(절대 조건 7)

---

## 4. 기능 요구사항 — 매핑

### REQ-012 (MUST) Deterministic Exact Match 우선
정규화된 필드명/식별자가 Registry의 공식 명칭, 별칭 테이블 또는
과거 승인 매핑과 정확히 일치하면 LLM 없이 `MATCHED`를 반환한다.
(절대 조건 5)

### REQ-013 (MUST) Deterministic 후보 검색
Exact match가 없으면 결정론적 검색(정규화 토큰, 접두/약어 사전,
전문 검색 인덱스)으로 상위 N(기본 10) 후보를 산출한다. 후보는 항상
Registry record다.

### REQ-014 (MUST) LLM 역할 제한
LLM은 (a) REQ-013 후보 목록의 재순위화, (b) 사람 검토용 설명 생성에만
사용한다. LLM은 후보 목록 밖의 코드를 추가할 수 없고, 최종 상태
(MATCHED/REVIEW_REQUIRED/NO_MATCH)를 결정할 수 없으며, 검증 판정에
관여할 수 없다. LLM 출력은 후보 id 순열 + 자유 텍스트 설명으로 제한된
구조로 파싱되고, 후보 집합을 벗어난 id는 폐기된다. (절대 조건 4)

### REQ-015 (MUST) Confidence 정책
각 매핑 후보에 `confidence`(0.0~1.0, 결정론 점수와 재순위 결과의 합성)를
부여한다. 임계값(기본: MATCHED ≥ 0.90, REVIEW_REQUIRED ≥ 0.40) 미만이면
자동 확정하지 않는다.
- confidence ≥ match 임계값 그리고 단독 우세 후보 → `MATCHED`
- 그 외 후보 존재 → `REVIEW_REQUIRED` (후보 목록 포함)
- 후보 없음 또는 review 임계값 미만 → `NO_MATCH`
LLM 재순위화는 임계값을 우회할 수 없다. (절대 조건 6)

### REQ-016 (MUST) LLM 불가용 시 대체 동작
LLM 호출 실패·시간초과 시 결정론 점수만으로 처리하되, exact match가
아닌 모든 결과는 `REVIEW_REQUIRED` 이하로만 반환한다 (fail-closed).

### REQ-017 (SHOULD) 승인 매핑 재사용
사람이 승인한 매핑(approved mapping memory)은 별도 테이블에 저장하고
동일 source 서명(정규화 필드명 + source system + version)에 대해
deterministic exact match로 재사용한다. 승인 이력은 audit 대상이다.

---

## 5. 기능 요구사항 — 검증

### REQ-018 (MUST) 데이터 타입 검증
매핑된 필드의 샘플 값(존재 시)을 Registry의 Data Element 타입 정의와
결정론적으로 대조한다 (문자열/수치/정수/불리언/날짜·시간).

### REQ-019 (MUST) 형식(Format) 검증
Registry가 형식(패턴, 길이, 자릿수 등)을 정의한 경우 이를 결정론적으로
검증한다. Registry에 형식 정의가 없으면 `FORMAT_UNDEFINED` WARNING으로
보고하고 통과 처리하지 않는다.

### REQ-020 (MUST) 단위(Unit) 검증
입력이 단위를 선언한 경우 Registry 단위 정의와 대조한다. 단위 환산은
승인된 환산 규칙 테이블에 있는 경우에만 제안하며, 자동 적용하지 않는다.

### REQ-021 (MUST) Code List 검증
Data Element가 Code List를 참조하면 샘플 값이 해당 version의 Code List
값 집합에 속하는지 결정론적으로 검증한다. Code List 미해소 시
`CODE_LIST_UNRESOLVED`로 보고한다.

### REQ-022 (MUST) Reference Model 문맥 검증
매핑 대상의 Reference Model 문맥(Path, Level, Kind of Object, 반복
Occurrence)을 조회해 (a) 입력 구조상 위치와의 정합 신호, (b) 동일
Data Number의 다중 Occurrence 존재를 보고한다. 문맥 정보는 판정 근거로
포함하되 자동 매핑 확정에 단독 사용하지 않는다.

### REQ-023 (MUST) 검증 판정 상태
검증 보고서는 필드별 Finding(severity: ERROR/WARNING/INFO, ruleId,
근거 record)과 전체 상태(PASS/WARNING/FAIL)를 포함한다.
- ERROR ≥ 1 → FAIL
- WARNING ≥ 1, ERROR = 0 → WARNING (human review 필요 플래그)
- 그 외 → PASS
검증은 전부 deterministic code로 수행한다. (절대 조건 5)

### REQ-024 (MUST) 민감 값 정책
Finding의 `actualValue`는 데이터 분류에 따라 원문/마스킹/해시/미기록을
적용한다. 기본값은 마스킹이며, 분류 미상 입력은 해시만 기록한다.

---

## 6. 기능 요구사항 — 출력·감사

### REQ-025 (MUST) 출력 계약
매핑 응답은 `schemas/mapping-response.schema.json`, 검증 보고서는
`schemas/validation-report.schema.json`을 준수한다. 계약 위반 응답은
서버 오류로 처리하고 반환하지 않는다.

### REQ-026 (MUST) Audit Log
모든 요청·매핑 결정·검증 판정·게이트 차단·LLM 호출(모델, 후보 입력 id
목록, 반환 순열)은 append-only audit log에 `inputHash`,
`compendiumVersion`, correlation id와 함께 기록한다. audit record에는
원본 payload를 저장하지 않는다(해시만). (절대 조건 9)

### REQ-027 (MUST) Normalized Output 분리
정규화 산출물(정규화 필드명, 표준화 타입 표현, 매핑 결과)은 원본과
별도의 출력 객체로 생성한다. (절대 조건 8)

### REQ-028 (MUST) Fixture 전용 샘플 값
테스트·문서·데모에서 사용하는 IMO 값 예시는 `tests/fixtures/` 파일에서만
읽는다. 소스 코드와 스키마 example에 실제 IMO Data Number를 하드코딩하지
않는다. 스키마 예시는 명백한 가상 표기(`IMO0000` 금지 대신 fixture 참조
설명)로 대체한다. (절대 조건 10)

---

## 7. 비기능 요구사항

### REQ-029 (MUST) 기술 스택 고정
Python 3.12, FastAPI, Pydantic v2, SQLite, SQLAlchemy, pytest,
JSON Schema(draft 2020-12), OpenAPI 3.1.

### REQ-030 (MUST) 결정론·재현성
LLM 재순위화를 제외한 전 경로는 동일 입력·동일 Registry version에 대해
byte 동일 결과를 반환한다. 시간·랜덤·UUID를 결과 본문에 사용하지 않는다
(correlation id는 audit 전용 필드로 분리).

### REQ-031 (MUST) Pydantic 단일 원천
요청/응답/보고서 모델은 Pydantic v2가 단일 원천이며, JSON Schema와
OpenAPI 3.1은 모델에서 생성·동기화 검사한다. 수기 스키마(본 설계 단계
산출물)는 구현 시 생성 스키마와 drift 검사로 대체한다.

### REQ-032 (SHOULD) 성능 목표
100 필드 배치 기준 deterministic 경로 p95 ≤ 2초(LLM 제외),
LLM 포함 p95 ≤ 15초. Registry 조회는 인덱스 기반이어야 한다.

### REQ-033 (MUST) 오류 시 Fail-closed
Registry 미적재, version 불일치, 계약 위반, 게이트 실패 등 모든 오류는
부분 성공 없이 해당 필드 또는 요청 전체를 명시적 오류 상태로 반환한다.

### REQ-034 (MUST) 테스트 요구
pytest 기반으로 (a) exact match, (b) 후보 검색, (c) confidence 경계,
(d) 게이트 차단(미존재 코드 주입 시), (e) 검증 5종(타입/형식/단위/
코드/문맥), (f) LLM mock 재순위화 경계, (g) 계약(스키마) 테스트를
포함한다. LLM 실 호출 없는 오프라인 실행이 가능해야 한다.

### REQ-035 (SHOULD) 관측성
구조적 로그(JSON), correlation id 전파, 매핑 상태별 카운터 메트릭을
제공한다. 로그에 원본 값 원문을 남기지 않는다 (REQ-024 정책 준용).

---

## 8. 절대 조건 ↔ 요구사항 추적표

| 절대 조건 | 요구사항 |
|---|---|
| 1. IMO Code 생성·추측 금지 | REQ-006, REQ-007 |
| 2. 미존재 IMO Code 반환 금지 | REQ-006, REQ-007, REQ-033 |
| 3. version + 근거 record 포함 | REQ-008, REQ-009 |
| 4. LLM은 재순위화·설명만 | REQ-014, REQ-016 |
| 5. exact match·validation 결정론 | REQ-012, REQ-018~REQ-023, REQ-030 |
| 6. confidence 미만 시 REVIEW_REQUIRED/NO_MATCH | REQ-015, REQ-016 |
| 7. XMO 별도 namespace | REQ-011 |
| 8. 원본 불변 + normalized 분리 | REQ-003, REQ-027 |
| 9. audit log + input hash | REQ-004, REQ-010, REQ-026 |
| 10. 샘플 IMO 값 fixture 전용 | REQ-028 |
