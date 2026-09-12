# K-MDS 3차년도 실증 검증 진행 기록 (PROGRESS_FILE)

과제: (RS-2024-00454634) 스마트·자율운항선박-밸류체인 간 데이터 표준개발 및 서비스 설계
주관: 한국선급 / 역할: K-MDS Orchestrator (3차년도 실증 총괄)

## 불변 상수
- PROJECT_ROOT: C:\kr-dev\k-mds
- DOCS_DIR: C:\kr-dev\k-mds\docs\(RS-2024-00454634 ) 스마트·자율운항선박-밸류체인 간 데이터 표준개발 및 서비스 설계
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
| C01 IDS 기본 공유 절차 | #4 정합율 | 유엔젤 Provider→Broker/DAPS→Consumer 3사 | 외부(K-MDS 220.76.220.247) |
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
  2. 외부 K-MDS(220.76.220.247) 접속 허용 여부 및 9.16 데모와의 관계.
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
