# K-MDS

국가연구개발과제 RS-2024-00454634 「스마트·자율운항선박-밸류체인 간 데이터 표준개발 및 서비스 설계」의
한국선급(KR) 작업 저장소. 과제 문서, 사업관리 자료, KR 담당 SW(환경규제 보고 데이터 표준·API·AI 활용 분석 서비스)를 한곳에서 관리한다.
과제 종료 2027-03-31. 산출물 수준은 서비스 설계 TRL4이며 상용 운영 시스템이 아니다.

## 폴더 지도

| 경로 | 내용 | 수정 |
| --- | --- | --- |
| `docs/` | 과제 수행 결과 문서 전체(공고, RFP, 계획서, 연차보고서, 산출물) | 제출본은 읽기 전용 |
| `docs/agent/pm-agent-design.md` | 사업관리 AI Agent 프롬프트 설계서(사람이 읽는 설계 기록) | 가능 |
| `pm/` | 사업관리: `PROJECT_FACTS.md`, `kpi/`, `budget/`, `decisions.md`, `meetings/`, `drafts/`, `evidence/` | 가능 |
| `ontology/`, `schemas/`, `data/`, `src/k_mds/`, `scripts/`, `tests/` | IMO Compendium 온톨로지와 k-mds 패키지(빌드: `uv run python scripts/dev.py build`). 세부 규칙은 `.claude/rules/k-mds-core.md` | 가능. `*/generated/`는 직접 수정 금지 |
| `verification/` | 3차년도 실증 검증 작업(C01~C07, `progress.md`, `evidence/`) | 가능 |
| `shared/standard-model/` | 표준 모델 단일 원본: `data-model.md`(ER, IMO번호), `openapi.yaml`(Ship-ODMS API), `gaps.md` | 가능. 앱 3종이 참조 |
| `apps/data-space/` | Ship-ODMS(GHG 의무보고 데이터, IMO Compendium 기준) API 서버. python/java/dotnet/javascript 구현 | 가능 |
| `apps/kr-ghg-ai-agent/` | IDS 서버로 수신한 데이터를 표준 모델로 매핑해 data-space 또는 KR-GEARs로 전달하는 자동화 Agent PoC | 가능 |
| `apps/imo-compendium-mapping-validator/` | 표준 모델 매핑 검증 서비스(Registry 적재·매핑·검증 API) | 가능 |
| `refs/regulations/` | 규정·표준 원문(라이선스 범위 내) | 읽기 전용 |
| `_archive/` | 통합 이전 자료, 폐기 후보 | 건드리지 않는다 |

## 데이터 흐름

IDS 서버 → `apps/kr-ghg-ai-agent` (표준 모델 매핑) → `apps/data-space` API 또는 KR-GEARs.
매핑 규칙과 스키마는 `shared/standard-model/`이 원본이다. 앱 안에 스키마 사본을 두지 않는다.
사본이 필요하면 빌드 단계에서 생성하고 git에 올리지 않는다.

## 반드시 지킬 것

- 과제 수치(목표, 예산, 일정, 담당)는 `pm/PROJECT_FACTS.md`가 기준이다. 기억이나 다른 문서의 수치로 대체하지 않는다.
  현재 실적은 `pm/kpi/*.csv`, 집행액은 `pm/budget/`의 최신 파일에서 읽고 `as_of` 날짜를 함께 말한다.
- `docs/`의 제출본(계획서, 연차보고서, 공문)은 고치지 않는다. 수정이 필요하면 새 파일을 만든다.
- 실선 운항 데이터, KR-GEARs 추출 데이터, IDS 인증서·키, `.env`는 git에 올리지 않고 외부 서비스로 보내지 않는다.
  테스트는 `tests/fixtures/`의 합성 데이터로 한다.
- 규제 보고 수치(연료소모량, CO2, CII 등)는 코드로 계산한다. LLM 출력값을 보고 수치로 쓰지 않는다.
- IMO번호, ISO 19848 채널 ID, MEPC 결의 번호, 조항 번호는 `refs/` 또는 `ontology/`에서 확인된 것만 쓴다. 없으면 "미확인"으로 남긴다.
- 매핑에서 대응 요소가 없으면 억지로 붙이지 말고 `shared/standard-model/gaps.md`에 갭으로 기록한다.
- 참여연구원 개인정보(연락처, 연구자번호, 인건비 단가)를 코드, 문서, 커밋 메시지에 옮기지 않는다.
- 메일·공문은 `pm/drafts/`에 초안만 만든다. 발송, IRIS·RCMS 입력, `git push`는 사람이 한다.

## 작업 규칙

- 앱마다 자체 README의 실행·테스트 명령을 따른다. 변경 후 해당 앱의 테스트를 돌리고 결과를 보고한다.
- 커밋은 앱 단위로 나누고 메시지 앞에 범위를 붙인다: `data-space:`, `ghg-agent:`, `validator:`, `ontology:`, `pm:`, `docs:`.
- 용어는 계획서 문구를 따른다. "AI Agent"는 계획서의 "AI 활용이 가능한 분석 서비스 설계"에 해당한다고 밝히고 쓴다.
- 문서·주석은 한국어, 코드 식별자와 API 필드명은 영어.
