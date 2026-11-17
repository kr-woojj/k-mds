# K-MDS 3차년도 실증 검증 진행 기록 (PROGRESS_FILE)

과제: (과제 문서 폴더)
주관: 한국선급 / 역할: K-MDS Orchestrator (3차년도 실증 총괄)

## 불변 상수
- PROJECT_ROOT: C:\kr-dev\k-mds
- DOCS_DIR: C:\kr-dev\k-mds\docs\(과제 문서 폴더)
- WORK_DIR: C:\kr-dev\k-mds\verification
- CASE_LIST: WORK_DIR\verification_cases.json
- EVIDENCE_DIR: WORK_DIR\evidence\{case_id}\

---

## 세션 S01 — 2026-09-12

### 시작 루틴
1. PROGRESS_FILE: 부재 → 본 파일 신규 생성.
2. CASE_LIST: 부재 → 과제 문서에서 초안 도출 예정(pass_criteria.confirmed=false).
3. 시뮬레이터 smoke: `simulator_run` 도구 **부재**. `standard_lookup` 도구 **부재**.
   - 대체 환경 점검: `uv run python scripts/dev.py build` → exit 0, k_mds 0.1.0 (evidence/_env/S01_env_smoke.log)
   - 저장소 상태: README "Repository Bootstrap 단계". 데이터 파이프라인·MCP·LangGraph 미구현. 시뮬레이터 코드 없음(grep "simulat" 0건).
4. pending 항목 선택: CASE_LIST 부재로 불가.
5. 이번 세션 목표: **부트스트랩** — DOCS_DIR 3차년도 문서(수정사업계획서, 실증협의 1·2차, 착수회의, 2차년도 연차보고서)에서 검증 항목 초안(CASE_LIST)을 도출하고 사람 확인 요청.

### 참고: 문서 판독 환경
- DOCS_DIR는 k-mds git에서 untracked(2026-09-12 배치). 커밋 대상 아님(대용량 PDF).
- 3차 실증협의(260916) 폴더는 비어 있음(회의 예정).
- hwpx/pptx는 zip+xml, pdf는 Read 도구(pages) 또는 시스템 python pypdf 6.18.1로 판독 가능.

### 워커 위임 (S01)
- W1: 3차년도 수정사업계획서_260515.pdf → 목표·지표·실증범위·표준·역할
- W2: 실증협의 1·2차 발표/회의록/RIMS/KR pptx/유엔젤 매뉴얼 → 시나리오·주체·데이터·결정사항·합격기준 언급
- W3: 착수회의 기관별 발표 7건 + 2차년도 연차보고서 → 기존 산출물·표준·시뮬레이터 존재 여부

(결과는 아래 "결정 및 미해결"에 이어서 기록)

### 워커 결과 (S01)
- W1 채택: analysis/S01_W1_3차년도_수정사업계획서.md (251p 전수, 페이지 근거 있음)
- W2 채택: analysis/S01_W2_실증협의_1_2차.md (7파일, 이미지 페이지 렌더링 판독 포함)
- W3 채택: analysis/S01_W3_착수회의_2차년도보고서.md (8파일)
- 반려 없음. 워커 간 불일치 3건 기록(코드북 건수, 예산, 표준 모델 그룹 수) → 사람 확인 항목.

### CASE_LIST 초안 작성 (verification_cases.json, 7건, 전부 confirmed=false)
| case_id | 대응 성능목표 | 발신→수신 | 실행 환경 |
|---|---|---|---|
| C01 IDS 기본 공유 절차 | #4 정합율 | 유엔젤 Provider→Broker/DAPS→Consumer 3사 | 외부(K-MDS <K-MDS-IDS-HOST>) |
| C02 GHG 표준 스키마·정합율 | #6, #4, #1 | RIMS 시뮬레이터→ROC(코드북)→Provider→KR | 로컬 가능(스키마·샘플 미확보) |
| C03 포트콜 JIT 이벤트 메시지 | #7 | RIMS SIM→ROC→Provider→RIMS 해운 Consumer | 외부 |
| C04 MSW 의무보고 메시지 | #8 | 선사/대리점→Broker→KLNET | 외부 |
| C05 보안·정책 예외 처리 | #4 | Consumer↔DAPS/Broker↔Provider | 외부 |
| C06 KR 검증 블록→GEARs | #6 | Consumer→KR MCP→GEARs | k-mds MCP 미구현 + 외부 |
| C07 시뮬레이터 E2E(TTA) | #9 | 전체 | 외부 + TTA 입회 |

### 착수 전 정리 — 다음 세션 착수 후보 C02 (KR 주관 항목, 유일하게 로컬 실행 가능)
1) 대응 목표·지표: 3차년도 KR 과업 "시뮬레이션 기반 선박 환경규제 보고 데이터 표준 모델/스키마 검증"(수정사업계획서 p.58); 성능목표 #6(IMO MEPC, 수요기업평가), #4 정합율 95%(IDSA Guide, 전문가평가), #1(ISO 18131).
2) 적용 표준·조항: IMO Compendium FAL.5/Circ.53(2024), ISO 19848:2024, IMO DCS/EU MRV, ISO 18131 DIS — 조항은 표준 근거 미확인(standard_lookup 부재).
3) 주체·데이터: RIMS 시뮬레이터(AMS/VDR) → ROC 표준변환(랩오투원 코드북 128항목) → IDS Provider → KR Consumer. 객체: KR 표준 모델 8그룹 184항목(JSON).
4) 측정 방법: JSON Schema 검증 PASS 건수/전체; 정합율 = 정합 항목/대상 항목 ×100 (초안, 분모 미정).
5) 예상 실패 지점: KR 스키마 파일 부재(2차년도 별첨 PDF만 존재 가능), 코드북↔KR 모델 항목 수 불일치(128 vs 184), 착수자료(8그룹) vs 연차보고서(7그룹) 불일치, 코드리스트(UN/LOCODE 등) 검증 데이터 부재.

### 결정 및 미해결 (S01)
- 결정: WORK_DIR 부트스트랩 완료. CASE_LIST 7건 초안. 실행 항목 없음(전부 기준 미확정).
- 결정: RIMS 포트콜 서비스 KPI(정시도착률≥80% 등, "예시" 표기)는 서비스 성능 지표로 판단, CASE_LIST 제외 → "범위 추가 제안"으로 분리.
- 사람 확인 필요:
  1. 7건 pass_criteria 확정(특히 정합율 산식·분모·목표, 전송 성공률·필수필드 충족률 산식).
  2. 외부 K-MDS(<K-MDS-IDS-HOST>) 접속 허용 여부 및 9.16 데모와의 관계.
  3. C02 입력물 확보: KR JSON Schema(설계서 별첨), 랩오투원 코드북 JSON, RIMS 시뮬레이터 샘플 → DOCS_DIR 또는 data/ 배치.
  4. 표준 조항 기입(standard_lookup 도구 부재) 또는 표준 원문 파일 배치.
  5. 문서 불일치 3건 해소(코드북 161/1,369 vs 330/1,100; 표준 모델 7 vs 8그룹; 3차년도 예산).
  6. 다음 세션 착수 항목: C02 권고(입력물 확보 시) / 그 외 C01(접속 승인 시).
- 미해결(과제 측): 128개 필수 데이터 목록·매핑표, 코드북·샘플 IDS 셋팅, 서비스별 메타 등록, 보안/정책 합의서, 인터페이스 기준서 — 2차 회의록에 완료 표시 없음.

세션 S01 종료 상태: NEEDS_INPUT

---

## 세션 S02 — 2026-09-12

### 사용자 결정 (지시)
- 첫 대상: 국제표준(ISO 19848, IMO Compendium) 기반 **GHG 환경규제 의무보고 데이터**.
- 흐름: 랩오투원 선박 플랫폼(IDS Provider) → IDS 서버 → GHG AI Agent(C:\kr-dev\kr-ghg-ai-agent) 매핑 → 표준 데이터 → KR-GEARs.
- 요청: 시나리오 검증 + 순차 시뮬레이션 준비(실행 아님).

### 시작 루틴
1. PROGRESS_FILE·CASE_LIST: S01 산출물 확인.
2. 시뮬레이터 smoke: kr-ghg-ai-agent(=이 시나리오의 시뮬레이터) `uv run pytest -q` → **1 failed / 32 passed / 90 skipped**; ruff 0; mypy 0. 증적 evidence/C02/precheck_S02/.
3. 선택 항목: **C02** (재정의). C06 은 C02 에 병합(merged).

### 시나리오 검증 결과
- 과제 문서 정합: KR pptx s.2 BLOCK A(시뮬레이터→ROC→IDS Provider)/BLOCK B(Consumer→KR MCP 검증→GEARs), 2차 회의록 Lane #3 GHG(Provider 랩오투원, Consumer KR), 착수 KR p.28 과 일치. **범위 추가 아님**(RFP4-3 KR 과업).
- PoC(kr-ghg-ai-agent UserManual "K-MDS Use Case #3") 와 사용자 시나리오 일치. Step 0~13, TC-01~15 정의됨.
- 차이/주의:
  a. ISO 19848 은 PoC 코드에 없음(grep 0건). PoC 매핑 기준은 IMO Compendium(FAL50)만. ISO 19848↔Compendium 매핑은 랩오투원 코드북 산출물.
  b. KR GEARs 제출 계약 PROVISIONAL(known-limitation L-2) → 정상 흐름도 최종 REVIEW_REQUIRED. "PASS"를 DELIVERED 로 정의하면 안 됨.
  c. 실 Provider(랩오투원) payload 형식·IDS envelope 미확보(L-1) → 합성 fixture 9종으로 1차 run.
- **Finding F-1**: tools/run_mock_e2e.py 는 최종 상태만 비교 → 검증기 부재로 전 fixture 가 GOVERNANCE_CANDIDATE_MAPPING_BLOCKED 인데 "overall=PASS" 출력. 판정 오라클로 부적합. run_c02.py 의 judge() 는 error 코드·mapping-result 존재·PROVISIONAL 변환을 함께 확인(selftest 로 검증).

### 전제 조사
- P1 imo-compendium-mapping-validator: C:\kr-dev, D:\kr-dev(없음), mcp.zip, GitHub kr-woojj 전부 **부재**. README 는 형제 디렉터리 전제. → 치명 블로커, 사람 제공 필요.
- P2 FAL50 xlsx: k-mds/data/raw/FAL50 에 없음(manifest pending_source). 공식 사이트 현재본 다운로드(scratchpad, sha256 5d2ed626…88a5, 시트 6개, Changes 소스 "EGDH 13/15"). **k-mds 에 배치하지 않음** — PoC registry 가 전제한 FAL50 본과 동일한지 미확인. 사람 확정 후 배치+manifest 갱신.
- P3 var/registry.sqlite3, candidate-inventory.json: P1·P2 선행.
- 실패 테스트 1건(test_governance)·skip 90건의 단일 원인 = P1~P3 부재. 코드 결함 아님.

### 산출물
- verification_cases.json: C02 재정의(stages 0~13, prerequisites P1~P4, rules R1~R7 초안, confirmed=false), C06 merged.
- run_c02.py: --dry-run(전제·기준 점검, exit 2) / --run(run_NN 자동 증가, step1 + mock E2E + judge) / --selftest(통과).
- evidence/C02/precheck_S02/: env, pytest, ruff, mypy, mock_e2e 로그, agent-evidence 8건(이관), FINDING.md, fal50_source.txt.
- kr-ghg-ai-agent 저장소: 변경 없음(reports/mock-e2e-results.json 원복, evidence/ 이관).

### 결정 및 미해결 (S02)
- 결정: C02 = 이번 실증의 1순위. 외부 Step 2·3 은 NOT_TESTED 허용(PARTIAL 상한, R7).
- 사람 확인 필요:
  1. **P1 검증기 저장소 제공**(경로 C:\kr-dev\imo-compendium-mapping-validator, uv 환경 포함). 없으면 C02 는 blocked.
  2. P2: 다운로드한 xlsx(sha256 5d2ed626…)를 FAL50 원본으로 인정할지, 또는 PoC 당시 원본 파일 제공.
  3. C02 pass_criteria R1~R7 확정(특히 R6 정합율 산식·분모 95%).
  4. 실 Provider 샘플(랩오투원 정오·동정보고 JSON) 제공 여부 — 없으면 합성 fixture 로 1차 run.
- 다음 세션: P1~P3 충족 + 기준 확정 시 `python run_c02.py --dry-run` → `--run` (run_01).

세션 S02 종료 상태: NEEDS_INPUT

---

## 세션 S03 — 2026-09-12 (진행 중, Step 0 체크포인트)

### 사용자 입력 반영
1. 검증기: github.com/kr-woojj/imo-compendium-mapping-validator → C:/kr-dev/imo-compendium-mapping-validator 클론(commit ad34c47), uv sync, 자체 테스트 71 passed.
2. FAL50 원본: k-mds/data/raw/FAL50/{IMO Compendium.xlsx, Readme.pdf, Changes.pdf} 배치 확인. xlsx sha256 5d2ed626…(S02 다운로드본과 동일). 스크래치 사본 삭제. source-manifest.yaml 갱신(files sha256, FAL.5/Circ.56, standard approved / ingestion pending).
3. IMO MEPC(SEEMP III·CII·DCS) 참조 — 필요 문서 목록을 사용자에게 제시(아래).
4. raw 배치: ISO19848(ISO 19848:2024 ed.2 PDF), 랩오투원(동정보고 코드북 336행, ISO19848 센서 코드북 TAG LIST 1,370행 등 7시트), 유엔젤(Provider/Consumer 매뉴얼, 외부접속 가이드, 시스템 구성·기본 시나리오, 실증 시연 v0.93).
5. 이후 Step 단위 확인 방식으로 진행.

### 시작 루틴
- smoke: P1~P3 충족 후 run_c02.py --dry-run → pass_criteria.confirmed 만 MISSING(exit 2, 의도된 동작).
- 선택 항목: C02 (계속).

### P3 구축 (evidence/C02/setup_S03/)
- prepare_registry: FAL50 import ok, elementCount 1205, occurrenceCount 2024, codeLists 57/codeValues 964, issueCount 0.
- build_candidate_inventory: 18 elements, sha256 22a01cdc…, source 5 fixtures.

### Step 0 실증 기준선 고정 — PASS (setup_S03/step0-baseline.yaml)
- agent commit e1a2295 clean / validator ad34c47 / Python 3.12.12 / uv 0.9.26
- governance flags = 매뉴얼 기대값과 일치(candidate_mapping_eligible true, 나머지 false); authority BOUND/BOUND/PROVISIONAL/PROVISIONAL/UNBOUND.
- 참고: 매뉴얼은 Git Root 를 D:/ 로 표기, 실제 C:/ — 드라이브만 상이.

### 체크포인트 (사람 확인 대기)
- C02 pass_criteria R1~R7 확정 요청(특히 R6 정합율 산식). 확정 전에는 Step 1 이후 판정을 기록하지 않는다.
- Step 1 진입 승인.

### S03 추가 입력: MEPC 문서 배치 (data/raw/MEPC/, source-manifest.yaml 에 sha256·제목 기록)
- MEPC.308(73), 336(76), 337(76), 338(76), 339(76), 346(78), 348(78), 355(78), MEPC/ES.2/2 Draft revised MARPOL Annex VI(2025, 초안).
- 336~339(76) 4건은 텍스트 추출 불가(이미지 PDF 추정) → 조항 인용 시 수동 판독. KR 지침은 사용자 결정으로 제외.

### Step 1 사전 확인 (판정 보류 — pass_criteria 미확정) setup_S03/step1-*.txt, step1-{health,ready,api_v1_governance}.json
- pytest 122 passed / 1 skipped(live_llm 자격증명 없음, PASS 불포함) / ruff 0 / mypy 0.
- /health ok; /ready READY(reference_model FAL50 1205, skill READY real_call, mcp OFF, llm mock, kr_gears_contract PARTIAL, delivery mock, governance BOUND); /api/v1/governance authorities BOUND/BOUND/PROVISIONAL/PROVISIONAL/UNBOUND.
- R1 초안 기준으로는 전 항목 충족. 기준 확정 시 Step 1 = PASS 로 기록 예정.

### 사용자 결정 (S03, 체크포인트 2 답변)
- "R7 확정" → R1~R7 전체 확정으로 해석·기록(R6 분모 기본안). owner_confirmed_by 우정재. C02 status designed.
- Step 2 진행을 위해 외부 K-MDS(유엔젤) IDS Provider 브라우저 접속 허용.
- Step 1 = PASS 확정 기록.

### Step 2 준비 (S03) evidence/C02/manual_S03/step-02/
- 유엔젤 문서(data/raw/유엔젤) 판독: 외부접속 가이드(접속정보·성공기준 8항), Provider 매뉴얼(Share Data→Meta→Policy→Representation→Catalogs→Brokers→Save), Consumer 매뉴얼(Data Consumption→Requests→REQUEST RESOURCE→BROKER 탭→Broker 선택→검색→Artifact→ACCEPT→Download/Dispatch), 시스템 구성(RIMS 수도권 서버, DAPS·Broker·Provider/Consumer Connector), 실증 시연 v0.93(샘플 메타데이터 기반, "향후 랩오투원 표준 모델과 연계").
- 도달성: Provider/Consumer UI 401(인증 요구), Connector API 200, Broker 405 → 서버 가동 중.
- Connector 관리 API 는 demo 계정으로 401 → UI 경로만 사용(자격증명 미공개).
- 브라우저로 Provider UI 기동. 사용자 UI 조작 대기.
- 예상 실패 지점: 현재 K-MDS 에 등록된 Offering 은 유엔젤 샘플(MDS Test/Guide Provider Data, provider-api:8086)일 가능성 — GHG(정오·동정보고) Dataset 미등록이면 Step 2 는 BLOCKED(매뉴얼 판정 기준) 또는 샘플 Dataset 으로 CONDITIONAL_PASS 결정 필요.

### S03 실행 결과 (Step 2~13)
- Step 2 CONDITIONAL_PASS: LAB021(랩오투원) 카탈로그의 "Noon Report API"·"DAQ Logger API" 식별(Provider Description 요청). Broker 검색 500/SPARQL 417 (F-4, 유엔젤 확인 요청).
- Step 3 CONDITIONAL_PASS: Agreement confirmed(87e0134a, e6913ae9), USE 2026-08-03~2030-12-31, Consumer Route "GHG Agent"(host.docker.internal:8001) 존재. 토큰·mTLS 는 간접 증빙(F-7).
- Step 4 수신 PASS: 실 payload Noon 14,101B / DAQ 29,640B (sha256 기록).
- run_01/run_02(fixture 9종): R1·R3·R4·R5·R6 충족. R2 는 문구 충돌(D1). 판정기 v1→v2 교체(R3 구현 결함 수정, 규칙 자체는 불변).
- 실 payload: 원본 → PROFILE_UNKNOWN(F-9); 코드북 어댑터 적용 → 프로파일 OK, 매핑 2~3/60 (F-10 후보집합 18개 제한, F-11 코드북 1:N 42/68, F-12 비표준 이벤트 코드, F-13 -9999 결측).
- C02 status: **partial**. 사람 결정 D1~D5 (verification_cases.json human_decisions_pending).

세션 S03 종료 상태: NEEDS_INPUT

### S03 추가 (사용자 결정·확인, 2026-09-12)
- 사용자 확인: Provider Backend Connection "TRIMSSIM Provider API" = vessellink loggers URL. 랩오투원(LAB021) 플랫폼 = **vessellink**. API 로 확인한 Backend Connection 6건 중 vessellink 2건(noon, loggers)이 LAB021 Offering 의 원천.
- 사용자 결정: Step 3 은 RIMS 서울사무소 IDS 서버에서 점검 예정 → CONDITIONAL_PASS 유지.
- Step 4 PASS: Consumer 수신본 ≡ vessellink 원본 (sha256 동일, Noon fb23ffbd… / DAQ 04317770…). 새 finding F-14(백엔드 무인증 공개), F-15(정적 스냅샷).
- 사용자 UI 재현 가이드: evidence/C02/manual_S03/step-04/BROWSER_TEST_GUIDE.md (Consumer UI 브라우저 기동 완료).
- Step 4 사용자 재현 완료: Consumer UI(CONNECTOR 탭) 다운로드본 2건 sha256 = API 수신본 = vessellink 원본 (browser-hash.txt). 캡처 2건 보존. Step 4 PASS 확정(재현 1회).

---

## 세션 S04 — 2026-09-13

### 사용자 지시
- data/raw/KR-Systems 에 KR-GEARs Type1 Voyage Template(Rev.2.1), Sample xlsx, Nexawave API URL 배치.
- IDS Consumer 로 받은 선박 환경규제 의무보고 데이터 → IMO Compendium 표준 매핑 → KR Systems API 데이터 리스트 변환 검증 → 보고용 PPT 1장(먼저 markdown).

### 시작 루틴
- PROGRESS/CASE_LIST: C02 partial(S03) 확인. 이번 과업 = C02 Step 7(매핑)·8(검증)·9(GEARs 변환)·11/12(입력 완전성) 로컬 수행. 시뮬레이터 smoke: S03 환경 유지(변경 없음).
- 근거 자료: GEARs_Template_Type1_Rev.2.1.xlsm(sha256 e7acd292…, Type 1 112열/그룹 7종, UNLOCODE 시트, Setting Cf표 Rev.2.1 2024-12-24), GEARs_Sample_Type 1.xlsx(0cc937a9…, 122행 샘플), Nexawave_URL.url → <KR-NEXAWAVE-HOST>/Api/Api (API 65종, GEARs 13종). 상세: /Api/ApiDetail?pApiId=64 "Post DCS/MRV Voyage Template" 필드 132개(필수 52), Token 헤더.
- 도구: verification/adapters/gears_voyage_transform.py (코드북+FAL50 registry+Code list+템플릿 → 매핑표·IMO 정준 이벤트·Type1 행·API 리스트·검증 보고). 산출물 evidence/C02/manual_S04/.

### S04 결과
- 표준 매핑: 71 필드 중 70 매핑(코드북 1:1 34, 연료구조 24, 최특정 9, 컨텍스트 3, 미해결 isEuPort 1). 이벤트 코드 EV01/02/16/10, BUNKERING·CARGO_WORK→EV28. 연료 Lsfo→VLSFO2020→GEARs HFO 열(FAL50 설명 근거, D6).
- GEARs Type1 변환: 레그 2건(레그1 PACTB→GTPRQ 완료: 124.4 h, 871.6 nm, HFO 54.96 MT, 벙커 599.97 MT; 레그2 미완료). 템플릿 검사 53건 PASS 36 / FAIL 6(필수 미도출) / WARNING 5 / 미완료 6.
- Nexawave API: Post DCS/MRV Voyage Template 132 필드(필수 52) 확보 → 데이터 리스트 생성, 레그1 필수 50/52. 전송 미실행(Token·endpoint 미확보).
- 판정 PARTIAL. 보고서 REPORT_GHG_GEARs_verification.md + GHG_GEARs_verification_1p.pptx. 신규 finding F-16~F-21, 결정 D6~D8.
- 도구 결함 수정 기록: UNLOCODE 시트 파서(A열 공백) 오류로 초기 실행에서 GTPRQ 를 미수록으로 오판 → 수정 후 재실행(PACTB 만 미수록, WARNING 로 조정).

세션 S04 종료 상태: NEEDS_INPUT (D6~D8, 랩오투원·GEARs 조치)
- S04 추가: 매핑 결과물 엑셀 1부 생성 — evidence/C02/manual_S04/GEARs_Type1_Mapping_Result_IMO00000009.xlsx (Sample 레이아웃 Type 1 시트 + 근거 시트 7종). 생성기 adapters/make_gears_excel.py. 검증: 행 JSON 의 수치값 전부 시트에 반영, LPG 등 표기 차이(공백) 정규화로 해결.

---

## 세션 S05 — 2026-09-16 (3차 실증회의일)
- 사용자 요청: IDS Provider 브라우저 기동, 라우트·브로커 리스트 점검, 가능하면 데모.
- 수행: Provider/Consumer Connector API 로 등록 현황 점검 + 데모(Description→Contract 201 confirmed→Artifact 200, 무결성 동일). Broker 검색 500 지속. 브라우저는 Provider/Consumer UI 기동(자동 클릭 불가).
- 신규 finding: F-22 vessellink noon 이벤트 0건(9/16), F-23 Provider Broker 미등록(Unregistered, 0 offers). RIMS 포트콜 자원 4건 신규 등록 확인(C03 참고).
- 판정: 데모 CONDITIONAL_PASS. 증적 evidence/C02/manual_S05/demo-20260916/.
세션 S05 종료 상태: NEEDS_INPUT (랩오투원 F-22, 유엔젤/RIMS F-23 확인)

## 증적 보관 메모 (2026-09-20)
- 참여기관 인프라 주소(K-MDS IDS 서버 IP·포트, KR nexawave API 포털 캡처, vessellink 테스트 URL)가 든 증적 81건은 공개 저장소에서 제외하고 `verification/evidence-private/`(git 제외, 로컬 보관)로 옮겼다. 보고서의 해당 경로는 `evidence/` → `evidence-private/`로 읽는다.

---

## 세션 S09 — 2026-09-26
- 사용자 요청: 실증 시나리오 정리 md + 데이터 흐름도 → 검토 답변 8건 수신(pm/decisions.md 2026-09-26 7줄).
- 산출: verification/scenarios/K-MDS_실증_시나리오_v0.1.md(전체 조망, 다이어그램 5), v0.2_S-1-1.md(범위 축소 절차서 초안, 흐름도 갱신, ISO 25023 정합성 항목 후보 M1~M5, 정합율 = M4 제안, 작업 W1~W8, D1~D8 쉬운 설명).
- 확인: data-space Ship-ODMS Java backend 로컬 :8088 가동(/api/ships 200, swagger 200) → KR GEARs 대역으로 사용. Consumer Route "Ship-ODMS API"·"GHG Agent" 등록 확인(실전송 미검증).
- 표준 근거 미확인: ISO/IEC 25023 원본 없음 → data/raw/ISO25023 배치 요청(W1). 측정 ID·산식 인용 보류.
- 미커밋(완료 시 일괄). 다음: 사용자 v0.2 검토·정합율(M4) 확정·D2/D4/D8 결정 → W2·W3 착수.

### S09 결과 (사용자 결정 5건 반영 후)
- W1: ISO/IEC **DIS** 25023:2014(E) 배치 확인(data/raw/ISO25000, sha256 38a6ac16…). 측정 ID 부여: M2=FCp-1-G, M3=FCr-1-G, M4=FCr-1-G(필드 단위), M1=CIn-2-G·M5=CIn-1-G(취지). 데이터품질은 25024 참조(8.4.2 NOTE). 정합율 = M4 채택.
- W4: 에이전트에 LAB021 코드북 사전 정규화 내장(lab021_ingress.py; 이벤트 컨텍스트·연료 구조·최특정 규칙·형 정규화·결측 null), 후보집합 0.2.0-provisional 159 요소(코드북 ID 합집합), normalization 컨텍스트 키에 IMO0140/0191/0603/0063/0065 추가. ruff/mypy 0, pytest 122 passed.
- 실 데이터 12 이벤트: 매핑 722/726(EXPLICIT 722, UNMAPPED isEuPort 4), 검증 FAIL 0(WARNING 195 PROFILE_NOT_APPLICABLE).
- W2/W3: imo_to_shipodms.py(Ship→Voyage→PortCall→PerformanceReport 중첩 POST), consistency_check.py(3자 대조, M1~M5).
- G-4: Ship-ODMS Java 백엔드 결함 수정 — saveReport 에서 자식 행 부모참조 설정, 목록 DTO 에 speedThroughWater·speedPropeller·speedProjected·speedOrder·courseOverGround·shipTrueHeading 추가. docker compose 재빌드.
- W8: run_s11.py. **run_01·run_02 PASS(T2 NOT_TESTED)**: M2 0.9945 / M3 1.0 / M4 0.9854(5/342 불일치 = seaHeight 정수형 G-5) / HTTP 오류 0 / 무결성 ok / 재현성 동일. 증적 verification/evidence/C02/s11/.
- T2(IDS 전달)는 apps/kr-ghg-ai-agent/.env 부재로 NOT_TESTED — .env.master 규약상 로컬 .env 를 두면 러너가 수행. 9/12·9/16 증적으로는 2/2 동일.
- W5 결정: Route 는 노트북 로컬 IP(유선 우선). 진해 현장에서 검증.
- 미결: TTA 의 25023 적용 판(DIS 2014 vs IS 2016) 확인(W7), 랩오투원 데이터 보강(W6), isEuPort 매핑 규칙(코드북 boolean vs UN/LOCODE 관할), Ship-ODMS fuelType 형(G-1)·seaHeight 형(G-5) 스키마 결정.
세션 S09 종료 상태: DONE (S-1-1 로컬 시험 PASS, 현장 T2/T3 및 TTA 합의 대기)

---

## 세션 S10 — 2026-09-26 (n8n 자동화)
- 사용자 요청: n8n MCP 로 S-1-1 실증 자동화 구성, GHG AI Agent docker 화, LLM = Gemini(추후 Open 모델), 실행 후 오류 분석, 평가단 열람 가능한 결과 제시.
- 구성: verification/automation/{compose.yaml, Dockerfile.harness, harness.py, README.md}. 컨테이너 kmds-ghg-agent(:8001, LLM_PROVIDER=gemini → OpenAI 호환 엔드포인트, 모델 gemini-2.5-flash, GEMINI_API_KEY 는 .env.master 에서 이름으로만 주입)·kmds-s11-harness(:8090, run_s11.py 단계 재사용, ship-odms 네트워크). n8n 워크플로 "K-MDS S-1-1 실증 자동화" (ID Pycuq2NaVtsIv3xJ, 웹훅 POST /webhook/kmds-s11, 노드 10: T0·T2 → 이벤트 분리 → T3~T5 에이전트 ingress 이벤트별 호출 → 취합 → T5 수집 → T6 → T7 → T8 → 응답).
- 코드 수정: (a) 에이전트 결함 — build_pipeline 이 make_llm_client 를 호출하지 않아 LLM_PROVIDER 와 무관하게 항상 mock 이던 문제 수정(orchestrator.py). (b) llm/client.py 에 gemini provider(OpenAI 호환) 추가. (c) run_s11.py 를 prepare_events/summarize_agent_run 으로 분리, T2 자격증명은 env 로도 수용, git 부재 허용. 에이전트 ruff/mypy 0, pytest 122 passed.
- 실행 결과(증적 verification/evidence/C02/s11/run_03~06, n8n 실행 3~6):
  - run_03: 파이프라인 전 단계 완료, 하네스 보고서 생성기 결함(A_mismatch 정수 len) → n8n 실행 3 오류. 수정 후 재판정 PARTIAL.
  - run_04: **오케스트레이터 운용 오류** — 실행 중 호스트에서 pytest 를 돌려 var/registry.sqlite3 잠금 경합 → SKILL_EXECUTION_ERROR 10건 → fail-closed 로 unmapped 증가(M2 0.9394). NOTE-interference.md 기록, 결과 미수정. 운용 규칙 README 추가.
  - run_05·run_06(무간섭): M2 0.9945 / M3 1.0 / M4 0.9854, HTTP 오류 0, 무결성 ok, **재현성 run_05≡run_06**. Gemini 실호출 4건/run(isEuPort 후보 제안, 후보 2건, skill 검증 미통과 → UNMAPPED 유지 = 설계대로). 측정치는 mock LLM 의 run_01·02 와 동일(결정적 매핑이 지배).
  - T2 IDS 전달: 자격증명 주입으로 실제 수행 — Consumer 아티팩트 수신 200, 274 B, events=[] → 원본(14,101 B)과 DIFFERENT(F-22 Provider 이벤트 0건 지속). 규칙 R-T2 FAIL → 종합 판정 **PARTIAL**. 나머지 6개 규칙 PASS.
- 평가단 열람: n8n UI(http://localhost:5678, Executions 노드별 입·출력) + 보고서 http://localhost:8090/runs/run_06/report (REPORT.md 동일) + Ship-ODMS UI(:3030) + 증적 sha256.
- 표준 근거: ISO/IEC DIS 25023:2014(E) (data/raw/ISO25000) 측정 ID 인용 유지. 그 외 표준 조항 인용 없음.
- 미결(사람 확인 필요): 랩오투원 Provider 데이터 복원(F-22) 후 T2 PASS 재실행; W7 TTA 25023 판; G-1/G-5·isEuPort; validator SQLite busy_timeout 권고(참조 저장소 수정 승인 필요).
세션 S10 종료 상태: DONE (자동화 가동, run_05·06 PARTIAL — 외부 F-22 만 미충족)

### S10 추가 — AI Agent 대화형 자동화 (n8n MCP)
- 사용자 요청: 대화 입력 → IDS Consumer 수신 → GHG 매핑 스킬 → Ship-ODMS 입력을 AI Agent 중심으로 자동화.
- 구성: 하네스에 도구 엔드포인트 6종 추가(/tools/fetch·map·deliver·consistency·judge·status; T3~T5 루프는 하네스가 수행). n8n 워크플로 "K-MDS GHG 데이터 AI Agent (대화형)" ID toAlr11gvHNYHvvy — Chat Trigger(공개 채팅 /webhook/kmds-ghg-agent-chat/chat) → AI Agent(Gemini, 메모리 20턴, 재시도 3회/45s) → HTTP Request Tool 6개($fromAI 로 run_id·source 전달). 시스템 프롬프트: 절차 순서, 수치는 도구 응답만 보고, Provider 0건이면 보관본 사용 여부를 사용자에게 질의, 입력 의도 있을 때만 Ship-ODMS 전송.
- 실행: 첫 턴에서 에이전트가 fetch_ids_data 호출 → Provider 이벤트 0건(F-22) 인지 → 사용자에게 보관본 사용 질의(설계대로). 동의 턴에서 run_08 을 보관본으로 map→deliver→consistency→judge 순차 호출, **PASS (T2 NOT_TESTED)** M2 0.9945 / M3 1.0 / M4 0.9854, Ship 1·Voyage 1·PortCall 2·Report 12, LLM 4회. n8n 실행 13(18:01~18:04Z), 보고서 http://localhost:8090/runs/run_08/report.
- 오류 분석: (1) Gemini 무료 티어 gemini-2.5-flash 는 모델별 일 20 요청 한도(429, quotaId GenerateRequestsPerDayPerProjectPerModel-FreeTier) — 파이프라인 4회/run + 대화 에이전트 턴당 6~7회로 소진. (2) gemini-2.5-flash-lite 는 신규 사용자 404, gemini-3.5-flash/-lite·3.7·3.8 은 503(high demand). 프로브 결과 gemini-3.6-flash·3-flash-preview·3.1-flash-lite 응답 → **gemini-3.6-flash** 로 전환(컨테이너 LLM_MODEL 오버라이드 + n8n 모델 노드), 성공. compose 기본값은 gemini-2.5-flash 유지(README 에 우회 절차). (3) 에이전트가 fetch 를 중복 호출해 빈 run 이 생기는 문제 → /tools/fetch 를 멱등화(이미 fetch 된 run_id 면 현재 상태 반환). (4) 실행 도중 사용자/평가자가 n8n UI 채팅으로 시도한 실행(14~16)이 run_09·run_10 을 생성(IDS 0건 단계에서 대기) — 증적 보존.
- 미완 run(run_07·09·10)은 LLM 429/503 또는 대화 중단으로 fetch 단계까지만 남음. 삭제하지 않음.
세션 S10 종료 상태: DONE (웹훅 자동화 + AI Agent 대화형 자동화 가동, run_08 PASS)

### S10 추가 — Ship-ODMS 프론트엔드 점검 (사용자 요청: 전달 데이터 화면 확인)
- 프론트엔드 호스트 포트 3030 이 langfuse-worker(127.0.0.1:3030)와 충돌해 접속 불가 → 3031 로 변경(apps/data-space compose). 화면: http://localhost:3031/ships/4/voyages/2/performance-reports (선박 4 = IMO 00000009, 보고 96건 = 12건 × 8 run 누적).
- G-6 Ship-ODMS 프론트엔드/백엔드 결함(전달 데이터와 무관한 기존 결함, 수정): (a) Voyage.YearReportId int→int?(null 역직렬화 실패로 항차 목록 페이지 오류), (b) WeatherDetails 풍향·기온 int?→double?, (c) 백엔드에 없던 라우트 3종 추가 LegReportController — 레그(PortCall ATD~ATA) 범위 보고 목록/상세, foc-fuel-type·foc-consumer-type 평면 목록. 모델 대조 스크립트로 전 필드 형 비교(나머지 불일치는 int→double 방향이라 무해).

### S10 추가 — GHG AI Agent 서비스 2종 (사용자 요청 2026-09-26)
- 구현: verification/automation/services.py + 하네스 도구 /tools/{query_ship, annual_ghg, dashboard}, 대시보드 페이지 /dashboard?run=run_NN. n8n AI Agent 워크플로에 도구 3개(query_ship_data, compute_annual_ghg, mapping_dashboard) 추가·시스템 프롬프트에 서비스 B/C 절차 명시.
- 서비스 B(조회·분석): IMO 00000009 조회 → CII 는 Ship-ODMS 표준모델(openapi.yaml)에 필드 없음 → 에이전트가 '없음' 보고 후 DWT 여부를 사용자에게 질의 → 연간 집계: 중복 보고 82건 제외 14건 사용, MGO 1.0 t·VLSFO2020 76.83 t, CO2 242.455 t, 거리 1,208.6 nm, GFI(TtW) 77.43 gCO2/MJ → YearPerformanceReport id 4 입력(HTTP 201). CF·LCV 근거 MEPC.308(73) Annex 5 표 p.5(data/raw/MEPC). 가정(사람 확인 필요): VLSFO→HFO 행(CF 3.114), 장비별 FOC 합=기간 소비량, TtW 만(WtW LCA 지침 미배치), CII 는 DWT 없어 미산출. 증적 verification/evidence/C02/s11/annual/.
- 서비스 C(대시보드): run_08 기준 총 726 / 변환 722 / 미매핑 4(isEuPort) / 전달 대조 342 중 일치 337·불일치 5(seaHeight G-5) / 대상 없음 16 / 코드북 변환 722 / 코드북 미해결 38(중복 타깃 cylOil 34, isEuPort 4). 에이전트가 표로 보고하고 dashboard_url 안내(n8n 실행 24).
- LLM 한도: gemini-3.6-flash 도 일 20회 소진(429) → 최종 답변 턴만 실패, 도구 실행·입력은 완료. gemini-3.1-flash-lite 로 전환해 재시도. 워크플로 모델이 UI 편집으로 2.5-flash 로 되돌아간 적 있음(실행 21·23) — 편집 후 모델 확인 필요.

### S10 추가 — Ship-ODMS DELETE /api/ships/{shipId} (사용자 요청 2026-09-26)
- ShipService.deleteShipCascade(@Transactional): 항차별 PerformanceReport(자식 JPA cascade) → PortCall → Voyage → YearPerformanceReport → Ship 순 삭제, 삭제 건수 응답. 없으면 404.
- 시험: DB 백업(ship_odms.db.bak-20260926T100641) 후 IMO 00000009 외 선박 3척 삭제(id 1: 항차 1·포트콜 1·보고 1·연차 1, id 2·3: 연차 1씩). 결과 선박 1척(00000009)만 잔존, 고아 행 0(voyage/report/yearly/fuel), 존재하지 않는 id 는 404. 증적 evidence/C02/s11/shipodms-delete-test_20260926.json.
- 주의: 사용자 요청의 IMO '0000000' 은 시험 선박 00000009 로 해석. 표준모델(shared/standard-model/openapi.yaml)에는 DELETE 미기재 — 반영 여부 사용자 결정.

### S10 추가 — 포털 이름 변경·메뉴 추가 (사용자 요청 2026-09-26)
- data-space 컨테이너·프로젝트·네트워크 이름을 K-MDS GHG Verifier 로 변경(kmds-ghg-verifier-backend/-frontend, 네트워크 kmds-ghg-verifier, compose name kmds-ghg-verifier). 하네스 compose 의 SHIP_ODMS_BASE·external network 갱신, 스택 재기동. DB(bind mount) 유지.
- 프론트엔드: 브랜드 K-MDS GHG Verifier(상단 바·탭 제목·lang=ko), 메뉴 순서 챗봇(/chat: n8n hosted chat iframe) → 선박 목록(/) → 대시보드(/dashboard: 하네스 매핑 증적 대시보드 iframe). iframe 주소는 Portal__ChatUrl/Portal__DashboardUrl 환경변수.
- 에이전트 컨테이너 재기동 시 LLM_MODEL 기본값(gemini-2.5-flash, 일 한도 소진)으로 돌아가므로 gemini-3.1-flash-lite 로 다시 오버라이드.

### S10 마감 — 보고서 초안·다음 일정 (2026-09-26 사용자 지시)
- TTA 공인시험 평가보고서 초안 v0.1(사용 매뉴얼 포함) 작성: verification/reports/TTA_시험평가보고서_S-1-1_v0.1_초안.md — 시스템 구성도(§1.4 배치·연결)·데이터 흐름도(§1.5) 포함. 연구책임자 검토·승인 후 Word·PPT 변환 예정.
- 미결 결정(W7 25023 판·증적 형식, G-1/G-5, isEuPort, LLM 키 등)은 **2026-10-01 대구 TTA(평가항목 구체화), KLNET, RIMS(오픈 모델 설치·API 노출 인프라 구성 스케줄 협의)** 후 사용자가 통보. 결정 후 **10-14 진도점검 데모 준비를 우선**하고 계속 진행.
세션 S10 종료 상태: NEEDS_INPUT (10-01 회의 결과 대기; 로컬 자동화·포털·보고서 초안은 준비 완료)


## 세션 S11 — 2026-10-08 (오픈 모델 전환·보안 정리)
- 비밀 값 관리를 `k-mds/.env` 한 곳으로 통일(템플릿 `.env.example`, `<sample: …>` 설명), `scripts/check_secrets.py` + pre-commit 훅 + CI 비밀 검사, `.gitignore` 에 pm/meetings·pm/tools (PR #1).
- RIMS 서울사무소 테스트 서버 오픈 모델(vLLM 기반 오픈 모델, OpenAI 호환, 발급 키) 반영: 에이전트 `LLM_DISABLE_THINKING`·`LLM_REASONING_EFFORT` 옵션 추가, openai provider 는 구조화 출력을 `json_schema` 방식으로. 컨테이너 재빌드 후 `/ready` llm.provider=openai real=true.
- 검증 run_13(n8n 웹훅 → 하네스 → 에이전트): T0~T8 완료, LLM 4/4 성공(중앙값 4.8 s), M2 0.9945·M3 1.0·M4 0.9854 — Gemini 실행 run_12 와 동일, 재현성 통과. 판정 PARTIAL 은 R-T2(Provider 이벤트 0건, F-22)만 false 로 이전과 같음.
- 대화형 AI Agent 워크플로 오픈 모델 본(`n8n/kmds-ghg-ai-agent-chat-openmodel.json`)은 서버가 tool-call 파서 없이 떠 있어 `400 tool choice requires --enable-auto-tool-choice` → 비활성 보관. RIMS 에 vLLM `--enable-auto-tool-choice --tool-call-parser hermes` 요청 필요.
- README 를 외부 사용자용으로 재작성(과제 식별 정보 제외), `docs/AI_SETUP_PROMPT.md`(AI 도구 자동 설치·검증 지시문) 추가.
- 2026-10-08 15:13~15:40(KST) RIMS 오픈 모델 포트가 닫혀(Connection refused) n8n 테스트가 timed out — n8n·자격증명 문제 아님(복구 직후 Simple AI Chatbot 2.6 s 응답). 복구 직후 run_14 는 T0·T2 노드가 3분을 넘겨 n8n 180 s 타임아웃(일시 현상, 이후 15 s). run_15 는 하네스 `/runs` 단독 호출로 생긴 T0·T2 전용 폴더. run_16(n8n 자동화) PARTIAL(R-T2 만 false), LLM 4/4(중앙값 3.1 s), M2·M3·M4 동일.
- 오픈 모델 사고 과정은 `chat_template_kwargs.enable_thinking=false` 로만 꺼진다. 시스템 프롬프트의 `/no_think` 는 효과 없음(사고 내용이 본문에 섞임). n8n OpenAI 노드는 이 파라미터를 못 넘기므로 챗봇 지연은 서버 기본값에 좌우된다. 포털(:3031/chat)은 여전히 Gemini 워크플로(`kmds-ghg-agent-chat`)를 가리킨다 — RIMS 가 tool-call 파서를 켜면 오픈 모델 본으로 전환.
- 2026-10-08 16:00 이후: RIMS 서버 재부팅으로 포트가 두 번째로 닫혔다 복구. n8n 두 워크플로의 오픈 모델 설정(OpenAI 노드 v1.2, 서버 지정 모델 호출명, temperature 0, 자격증명 "RIMS 오픈 모델 (OpenAI 호환)")은 동일했음. tool-call 파서 우회: 서버에 `tool_choice=none` 으로 보내면 모델이 본문에 `<tool_call><function=…><parameter=…>` 형식으로 답하는 점을 이용해 `verification/automation/qwen_tool_proxy.py`(compose `qwen-tool-proxy`, :8091)가 이를 OpenAI `tool_calls` 로 변환. n8n 자격증명 "RIMS 오픈 모델 via tool proxy"(Base URL host.docker.internal:8091/v1) 로 오픈 모델 챗봇 활성화 → get_run_status 7 s, mapping_dashboard 5.8 s, 보관본 전 과정 run_17 PASS(304 s, orchestrator n8n-ai-agent). 포털 `Portal__ChatUrl` 을 `kmds-chat-qwen-open-model` 로 전환(:3031/chat 이 오픈 모델 사용).

---

## 세션 S12 — 2026-11-13 (실선 샘플 데이터 전환 준비)
- 사용자 지시: 선주·선박관리사가 활용에 동의(2026-10-20 회신 메일, 원문은 저장소 밖 보관)한 2024년 컨테이너선 데이터를 랩오투원이 IDS Provider 에 등록(2척 중 1척) → 이 데이터를 시뮬레이션 기반 실증·시험평가(S-1-1)에 사용.
- 대상 자원: Consumer UI 기준 "Noon Report API"(키워드 noonreport·imocompendium·maritime, 제공 기간 2026-08-03~2030-12-31), Consumer 아티팩트 `4e70da45-4f33-495d-b3a9-5c07c0383e4e`. 기존 9/12 계약 아티팩트(f508740a…)와 다른 ID.
- 데이터 취급(AGENTS.md "실선 운항 데이터 git 금지·외부 서비스 전송 금지"): 수신본·증적은 전부 `verification/evidence-private/C02/realship/`(git 제외). LLM 은 mock(로컬 러너 기본값)으로만 실행 — Gemini·RIMS 오픈 모델 으로 실선 데이터를 보내는 것은 사용자 결정 전까지 하지 않는다. n8n·하네스 컨테이너 경로는 LLM_PROVIDER 가 실 모델이므로 실선 run 에 쓰지 않는다.
- 러너 수정(run_s11.py): `S11_EVIDENCE_DIR`(증적 루트 변경), `IDS_NOON_ARTIFACT_ID`(수신 아티팩트 지정), T2 오류 시 detail 기록(호스트 마스킹). 기본 동작은 그대로.
- **수신 시도 결과: BLOCKED(외부)**. 09:36 KST 신규·기존 아티팩트 모두 `ConnectError WinError 10054`(연결 강제 종료). Consumer(:26414)·Provider(:26412) 포트는 TCP 연결되나 TLS 핸드셰이크가 응답 없음(10 s 타임아웃) → 커넥터 서비스 또는 경로 문제로 추정, 자격증명·아티팩트 ID 문제 아님(기존 아티팩트도 동일). 증적 evidence-private/C02/realship/ids-inbox/probe-*/T2-ids-transfer.json.
- 로컬 Docker 데몬 미기동(Ship-ODMS :8088 없음) — run 전에 Docker Desktop·data-space compose 기동 필요.
- 복구 후 절차: (1) 수신본을 ids-inbox 에 보관(스냅샷, sha256 기록) → (2) `S11_EVIDENCE_DIR=verification/evidence-private/C02/realship/s11 IDS_NOON_ARTIFACT_ID=4e70da45-… … run_s11.py --run --source <스냅샷>` 2회(재현성) → (3) 이벤트 코드·연료 종류·결측이 시험 선박(00000009) 데이터와 다르면 갭은 shared/standard-model/gaps.md 에 기록.
- 사람 확인 필요: ① IDS 커넥터 상태(RIMS/유엔젤) ② 실선 run 에 RIMS 오픈 모델 사용 허용 여부(참여기관 서버지만 KR 외부) ③ TTA 보고서·공개 저장소에는 실선 측정치(M2~M4)만 싣고 원자료·선박 식별정보는 제외하는 방침 확인 ④ 2척 모두 필요한지(랩오투원 추가 설정 가능 회신).
세션 S12 상태: BLOCKED (IDS 커넥터 TLS 무응답)

### S12 추가 — 사용자 결정 반영·IDS 재점검 (2026-11-13)
- 결정(pm/decisions.md 2026-11-13 3줄): ① 1척으로 우선 진행 ② 실선 run 에 참여기관 오픈 모델 서버 사용 허용, 외부 공개 자료에는 특정 모델명 대신 일반 용어 ③ 공개물에는 측정치만, 원자료·식별정보 제외. 후속: 시험평가 보고서 작성, 프론트엔드 고도화(DB JSON 다운로드·CSV 변환).
- IDS 재점검 09:45 KST: Provider API·Consumer API 포트 TLS 핸드셰이크 10 s 무응답, Consumer UI 포트도 HTTP 응답 없음(TCP 연결만 성립) → 09:36 과 동일, 지속.
- 데모 셋업 스크립트(pm/tools/demo/demo_setup.ps1)는 에이전트 세션의 실행 권한 정책에 막혀 실행하지 못함 → 사용자가 데모_시작.cmd 로 직접 기동.

### S12 추가 — 실선 샘플 데이터 S-1-1 실행 (2026-11-17)
- IDS 서버 주소 변경(RIMS 공지) 반영: 새 주소에서 Provider API·Consumer API(TLS 응답)·Provider UI·Consumer UI(HTTP 401, 인증 요구) 모두 가동 확인(13:14 KST). 11-13 무응답의 원인 = 서버 이전. `.env` 의 IDS_CONNECTOR_BASE 는 사람이 새 주소로 갱신해야 한다(이번 run 은 환경변수로 덮어써 실행). 데모 스크립트의 IDS Consumer UI 탭도 .env 값을 따른다.
- 수신(T2): Consumer 아티팩트 4e70da45… HTTP 200, 62,832 B, sha256 5919f133…523b. 이벤트 54건(NOON_AT_SEA 20, ARRIVAL 8, CARGO_WORK 8, DEPARTURE_SBY 8, RUP 8, BUNKERING 2), 기간 2025-12-01~2025-12-30 UTC, 이벤트당 64 필드. **주의: 지시의 "2024년" 과 달리 수신 데이터 기간은 2025년 12월** — 랩오투원 확인 필요. general 에 선장 성명 필드가 있어 원자료는 evidence-private 밖으로 내보내지 않는다.
- 스냅샷: evidence-private/C02/realship/ids-inbox/noon-snapshot-20261117.json. 증적 루트 evidence-private/C02/realship/s11/.
- run_01·run_02: **무효(도구 결함)** — 에이전트 증적 커밋의 디렉터리 rename 이 Windows 일시 잠금으로 PermissionError(각각 13번째·15번째 이벤트, 실패 위치가 달라 일시적). 수정: apps/kr-ghg-ai-agent evidence.py 에 rename 재시도(5회·0.5 s). 에이전트 unit·contract 47 passed. 미완 run 폴더는 삭제하지 않음.
- **run_03·run_04: PASS** (LLM mock, T2 수행 PASS — 재수신본 ≡ 스냅샷). M2 0.9937(미매핑 21/3,317: isEuPort 18, bunkeringStopLtc 2, remark 1) / M3 1.0(FAIL 0/3,296, WARNING 864) / M4 0.9949(불일치 9/1,780: seaHeight 5·swellHeight 4, 정수형 절삭) / Ship-ODMS HTTP 오류 0(PortCall 8, Report 54) / 증적 무결성 ok / 재현성 run_03≡run_04. 에이전트 최종 상태는 54건 모두 REVIEW_REQUIRED(GEARs 계약 PROVISIONAL, 설계대로).
- 갭 기록: shared/standard-model/gaps.md(2026-11-17 절).
- 남은 일: ① .env 주소 갱신(사람) 후 오픈 모델 연결 경로(하네스·n8n)로 실선 run — 하네스 컨테이너에 S11_EVIDENCE_DIR·IDS_NOON_ARTIFACT_ID 전달 필요(compose 수정) ② 데이터 기간(2024 vs 2025-12) 확인 ③ 시험평가 보고서 반영(측정치만) ④ 프론트엔드 JSON 다운로드·CSV 변환(계획 먼저) ⑤ 표준모델 DB 에 실선 선박 1척 적재됨(로컬 DB, git 제외) — 데모 화면에 선명이 보이므로 공개 시연 전 표시 방침 결정.
세션 S12 상태: DONE (실선 1척 로컬 실증 PASS, 오픈 모델 경로 run 과 보고서 반영 대기)

### S12 추가 — 사용자 지시 6건 반영 (2026-11-17 오후)
- 결정: 데이터 기간은 추후 확인. 보안 사항으로 보이는 필드는 가명 처리. `.env` 필요한 값은 자동 반영. 백엔드·프론트엔드 고도화는 제안 → 승인 후 진행.
- `.env`: IDS_CONNECTOR_BASE 호스트를 새 주소로 교체(1줄). LLM_ENDPOINT 도 옛 호스트를 가리키지만 새 주소를 통보받지 못해 그대로 둠.
- 미매핑 재확인(FAL50 registry): bunkeringStopLtc → IMO0656, remark → IMO0606 을 lab021_ingress.PICK 에 추가(코드북 1:N 후보 중 최특정, 근거는 코드 주석·gaps.md). isEuPort 는 참조모델에 대응 요소 없음 → 갭 확정. 자체 검사 선실패 확인 후 구현, 에이전트 unit·contract 47 passed, ruff 는 기존 12건만(신규 0), mypy 기존 1건(llm/client.py).
- 불일치 재검증: seaHeight(IMO0632)·swellHeight(IMO0635) 는 FAL50 format `n..2` → 표준모델 DB 정수형이 참조모델과 일치. DB 수정하지 않음(Provider 소수 정밀도와 표준 형식의 갭으로 재분류, gaps.md). 실수형 전환 여부는 사용자 결정.
- 가명 처리(run_s11.mask_payload): 시험 선박(00000009)이 아니면 general 의 shipName·imoNo·callsign·mmsi·masterName 과 이벤트의 remark·ceName·masterName 을 고정 가명으로 교체(자료형 유지), 운항 수치는 불변. 원본은 스냅샷·T2 수신본(evidence-private)에만 존재. run_08 증적 전 파일에서 실 식별값 검색 0건. 표준모델 DB 의 실선 원본 선박은 백업(ship_odms.db.bak-20261117-realship, git 제외) 후 삭제, 가명 선박으로 재적재.
- run_05·06: 가명 MMSI 를 문자열로 넣어 IMO0326 형식 검증에 걸림(미매핑 +54, M2 0.9783) → 도구 결함, 자료형 유지로 수정. run_07: PARTIAL(재현성 규칙만 false — 직전 run 과 설정이 달라서). **run_08: PASS** (LLM mock) M2 0.9946(미매핑 18/3,317 = isEuPort 만) / M3 1.0(0/3,299) / M4 0.9949(9/1,780, 파고 정수형) / T2 PASS / HTTP 오류 0 / 무결성 ok / 재현성 run_07≡run_08.
- **오픈 모델 run: BLOCKED(외부)** — LLM_ENDPOINT 포트가 옛 호스트·새 호스트 모두 TCP 연결 후 HTTP 무응답(20 s). 새 엔드포인트 주소 통보 필요.
- 대기: 백엔드·프론트엔드 고도화 제안에 대한 승인.

### S12 추가 — 사용자 결정 4건과 오픈 모델 재확인 (2026-11-17 저녁)
- 결정: ① 파고·너울 저장형은 IMO Compendium 기준 우선(정수 `n..2` 유지, DB 불변 — 불일치 9건은 Provider 정밀도 갭으로 설명) ② 고도화 순서는 제안대로(B-1 → F-1 → F-2 → B-2·B-4 → F-3·F-4) ③ 프론트엔드 디자인 파일은 사용자가 올릴 예정 ④ 오픈 모델 주소를 IDS 서버 호스트(포트는 이전 그대로)로 바꿔 재확인. 백엔드·프론트엔드 작업은 위가 모두 풀린 뒤 다시 요청.
- `.env`: LLM_ENDPOINT 호스트를 IDS 서버와 같은 새 호스트로 교체(포트·경로 불변, 1줄).
- 재확인 결과: **여전히 BLOCKED(외부)** — 새 호스트의 오픈 모델 포트가 `/v1/models` 요청에 1회 연결 리셋(WinError 10054), 이후 3회와 TLS 시도 모두 시간 초과. 같은 호스트의 IDS Provider·Consumer API 포트는 TCP 정상. 서버 쪽에서 모델 서비스가 내려가 있거나 포트 포워딩이 빠진 것으로 추정(추정, 미확인).
- 대기: RIMS 에 오픈 모델 서비스 포트 확인 요청(사람) → 응답 오면 가명 처리된 실선 데이터로 오픈 모델 run. 디자인 파일 업로드.

### S12 추가 — 오픈 모델 실행, 백엔드·프론트엔드 고도화 (2026-11-17 밤)
- 오픈 모델 서버 복구 확인(모델 목록 HTTP 200). 가명 처리된 실선 데이터로 오픈 모델 실행: run_09 PASS(M2 0.9946 / M3 1.0 / M4 0.9949, LLM 호출 18회 = 미매핑 `isEuPort` 18건의 후보 제안, 확정 매핑은 mock 과 동일 → run_08 과 재현성 일치). T0 baseline 에 실제 provider 를 기록하게 함(모델명·주소는 적지 않음).
- 백엔드(표준모델 API, Java) — 표준 모델 1.1.0:
  - B-1 `GET /api/ships/{id}/export?format=json|csv` (중첩 JSON / 표별 CSV zip, UTF-8 BOM, 수식 주입 방지).
  - B-2 `PerformanceReport.voyageLegRemarks`(IMO0606) 추가, 전달 어댑터가 벙커 요소(IMO0656·0666·0667)를 `_BUNKER` 행으로 전달(G-6). 대상 없는 요소 19 → 15종.
  - B-3 파고·너울은 정수 유지(결정).
  - B-4 같은 항차·보고시각·이벤트 유형의 보고, 같은 항차·출항항·출항시각의 포트콜은 재전송 시 교체·갱신(누적 방지).
  - 런타임 이미지(jlink)에 `jdk.unsupported` 모듈 추가 — 없으면 생성자 주입 서비스의 @Transactional 프록시 생성이 실패해 기동하지 않음.
  - 테스트: `./gradlew test` 통과(임시 DB `build/test.db` 사용 — 실행 DB 를 건드리지 않게 기존 테스트도 수정). python·javascript 구현에는 미반영.
- 새 백엔드로 재실행(오픈 모델, 가명 선박 삭제 후): run_10 PARTIAL(재현성 규칙만 — 대조 항목이 늘어 M4 0.9949 → 0.995), **run_11 PASS** M2 0.9946 / M3 1.0 / M4 0.995(불일치 9 = 파고·너울) / HTTP 오류 0. 두 번 보낸 뒤 DB 는 보고 54·포트콜 8 그대로(누적 없음), 비고 1건·벙커 행 2건 저장 확인.
- 공개 시험 선박: run_21 PARTIAL(T2 404 — 이전한 IDS 서버에 예전 시험 artifact 가 없음, 재현성은 대조 항목 342 → 344 로 M4 0.9854 → 0.9855), run_22 PASS(--skip-ids, T2 NOT_TESTED). 시험 선박의 중복 보고 108건은 재전송으로 12건으로 정리됨.
- 프론트엔드(포털, Blazor):
  - F-1 선박 목록에 JSON·CSV 내려받기(포털이 백엔드 내보내기를 중계).
  - F-2 `정합성 대조` 화면(run 선택, 불일치만 보기, M2·M3·M4, 대조표, CSV 내려받기). 하네스에 `GET /runs/{id}/consistency`, `/consistency.csv` 추가, T7 이 `consistency-checks.csv` 를 남김(2026-11-17 이전 run 에는 CSV 없음).
  - F-3 KRDS 시각 언어(`design/krds.md`)와 Pretendard GOV(subset woff2 3종, OFL) 적용: `wwwroot/krds.css`, 사이드 내비게이션·표·버튼·배지·알림. 이모지 제거, 정부 식별 요소는 쓰지 않음.
  - F-4 표 머리글에 IMO 번호·단위(openapi 에서 확인한 것만), 운항 보고 표에 비고(IMO0606) 열, 챗봇 화면 문구에서 특정 모델명 제거.
  - 확인: `dotnet build` 오류 0, 포털 화면 2종 헤드리스 캡처, 내려받기 3종 HTTP 200.
- 한계·남은 일: 포털의 정합성 대조 화면은 하네스의 공개 증적 폴더(시험 선박)만 본다 — 실선 run 의 대조 CSV 는 `evidence-private/…/run_NN/shipodms/consistency-checks.csv`. 선명한 화면 모드(고대비) 미구현. 데이터 기간 확인, 시험평가 보고서 반영, 커밋은 미수행.

### S12 추가 — 초기화 후 재테스트, 포털 브라우저 점검과 수정 (2026-11-17 심야)
- 초기화: 표준모델 DB 선박 0척, 공개·비공개 S-1-1 증적과 에이전트 증적을 비움. 이전 자료는 `verification/evidence-private/_reset-backup-20261117/`(git 제외)에 보관. 공개 증적의 run 번호는 run_01 부터 다시 시작(예전 run_01~23 은 백업에만 있음).
- 재테스트(오픈 모델): 시험 선박 run_01·02 PASS(T2 NOT_TESTED, M2 0.9945 / M3 1.0 / M4 0.9855, 불일치 5), 가명 실선 run_01·02 PASS(M2 0.9946 / M3 1.0 / M4 0.995, 불일치 9). 2회차는 1회차와 측정치 동일.
- 브라우저 점검(전 화면 로딩, 클릭 흐름, 정합성 대조, 대시보드)에서 찾아 고친 것:
  - 대시보드가 비어 있던 원인: 스크립트 괄호 누락(커밋된 코드부터 있던 문법 오류) → 수정, run 선택·수치·차트 표시 확인.
  - 포털이 정적 렌더링이라 행 클릭·run 선택·체크박스·"불러오는 중" 표시가 동작하지 않던 것 → 상호작용 모드(사전 렌더링 끔)로 전환. 불러오는 동안 대기 커서·입력 차단이 실제로 나타나는 것을 확인.
  - 행 클릭 이동 주소에 선박 ID 가 비던 것(입출항·구간 보고) → 화면의 경로 값 사용.
  - 연료 소비 상세의 가로 넘침, 값이 없는데 "공선"으로 나오던 적재상태, 빈 항목뿐이던 보고 상세 화면(표준 모델의 26개 항목으로 교체), 없는 주소 안내, 템플릿 예제 화면 삭제.
  - 표 머리글 IMO 번호: 데이터 열 전부에 표기(하위 표 포함, openapi 설명 기준). 번호가 없는 열은 내부 ID 와 보고 연도(K-MDS 확장)뿐.
- 연차보고 연도: `YearPerformanceReport.report_year`(K-MDS 확장, FAL50 에 대응 요소 없음) 추가. 연간 GHG 집계가 보고시각(UTC) 연도로 나눠 계산하고(미지정 시 최근 연도), 선박·연도당 한 건으로 저장. 시험 선박 2026년, 가명 실선 2025년으로 기록 확인. 챗봇 도구에 year 인자 추가.
- 가명 실선의 연간 집계 증적이 공개 폴더에 생겨 비공개 폴더(`evidence-private/C02/realship/annual/`)로 옮김 — 하네스의 연간 집계 증적 경로는 공개 폴더 고정이므로 실선 선박으로 집계할 때 주의.
- 공개 기록 정리(2026-11-17): 이 문서의 예전 기록에서 특정 오픈 모델 이름을 일반 용어(오픈 모델)로 바꿨다. 파일·컨테이너 이름에 들어 있는 식별자는 실제 이름과 맞아야 해서 그대로 두었다. 새 공개 증적(run_01·02)의 에이전트 manifest 24개에서 `llm_model` 값도 `open-model` 로 바꿨다(manifest 는 file_hashes 대상이 아니어서 무결성 검사 결과는 그대로).

### S12 추가 — 정리 (2026-11-17 자정 무렵)
- 모델 이름 정리 범위 확대: tool-call 프록시 파일·서비스·컨테이너(`tool_call_proxy.py`, `tool-call-proxy`, `kmds-tool-call-proxy`)와 챗봇 웹훅 경로(`kmds-chat-open-model`)를 중립 이름으로 바꾸고 README·배포 문서·주석을 정리. 실행 중인 n8n 워크플로와 포털 설정에도 적용, 챗봇 새 주소 응답 확인. 남은 것은 서버가 요구하는 모델 호출명 값과 n8n 워크플로 내부 ID, `data/raw/RIMS/` 의 원문 안내서 파일명.
- 하네스의 연간 GHG 집계 증적: 시험 선박이 아니면 `verification/evidence-private/annual/` 에 쓴다.
- `.env`·`.env.example` 정리 스크립트 `scripts/tidy_env.py` 추가(쓰지 않는 LLM 제공자 항목 삭제, 변수 설명 주석, 주석의 모델 이름 정리). 값은 읽거나 출력하지 않는다. 실행은 사람이 한다.
- 불필요 파일 삭제: DB 백업 5개, 초기화 백업 폴더, IDS 수신 시험 조각, 폰트 zip, 쓰지 않는 n8n 파일, 빌드 산출물.
- SW 등록 제출 자료 초안: `pm/sw-registration/ghg-ai-agent/`(git 제외).
