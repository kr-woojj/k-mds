# K-MDS Use Case #3 — 선박 환경규제 의무보고 데이터 상호운용성 검증 결과
IDS Consumer 수신 데이터 → IMO Compendium(FAL50) 표준 매핑 → KR GEARs Type1 Voyage Template / Nexawave API 데이터 리스트 변환 검증
(과제 RS-2024-00454634 · 3차년도 · case C02 · 2026-09-13 · 작성 K-MDS Orchestrator · 검토 한국선급 연구책임자)

## 1. 검증 경로와 대상
```
vessellink(랩오투원 LAB021) ─Provider API─▶ K-MDS Provider Connector ─IDS(DAPS·계약)─▶ KR Consumer Connector
        ─▶ ① IMO Compendium 표준 매핑(코드북 + FAL50 registry) ─▶ ② KR GEARs Type1 Voyage Template(Rev.2.1)
        ─▶ ③ Nexawave "Post DCS/MRV Voyage Template" API 데이터 리스트 (전송은 미실행)
```
| 항목 | 값 |
|---|---|
| 입력 Dataset | "Noon Report API" (카탈로그 LAB021, publisher vessellink) — Consumer 수신본 = 원본, sha256 `fb23ffbd…` 동일 |
| 선박·기간 | IMO 00000009 TEST_BULK_DIESEL_09 (시뮬레이터 선박), 2026-04-19 ~ 04-30, 이벤트 12건 / 필드 71종 |
| 항로 | PACTB(Cristobal) → GTPRQ(Puerto Quetzal) → PEPLO(진행 중) |
| 표준 근거 | IMO Compendium FAL50(FAL.5/Circ.56) 1,205 요소·Code list(Event type EV01~29, Fuel type 25종) / Provider 코드북 156항목 |
| 대상 규격 | GEARs_Template_Type1_Rev.2.1.xlsm(112열, [DCS,MRV] MANDATORY 15열 + 연료 10종×4열 + 벙커링/보정) / Nexawave API pApiId=64 (132 필드, 필수 52, Token 헤더) |

## 2. ① 표준 매핑 결과 (Provider 필드 → IMO Compendium)
| 구분 | 건수 | 비고 |
|---|---|---|
| 매핑 완료 | **70 / 71 (98.6 %)** | 미해결 1: `isEuPort` (IMO0856/0857 관할구역 코드와 형식 불일치, boolean) |
| 코드북 1:1 | 34 | 예: voyNo→IMO0191, hourSlr→IMO0600, steamingDistanceSlr→IMO0613 |
| 연료 구조 해소 | 24 | consumption{Me,Ge,Blr,Other}{연료} → FAL50 "Consumption By Fuel Type"(IMO0654 연료코드 + IMO0670/0893/0673/0903) |
| 최특정 요소 선택 | 9 | draftFore→IMO0621, draftAft→IMO0622, shipCourse→IMO0332 등 |
| 이벤트 컨텍스트 | 3 | portCode/portName/dateEventUtc → 도착(IMO0108/0109/0063)·출발(IMO0111/0112/0065) |
| 이벤트 코드 변환 | 6종 | ARRIVAL→EV01, DEPARTURE_SBY→EV02, NOON_AT_SEA→EV16, RUP→EV10(추정), BUNKERING·CARGO_WORK→EV28(전용 코드 없음) |
| 연료 코드 변환 | 6종 | Hfo→HFO, Lsfo→VLSFO2020, Ulsfo→ULSFO2020, Do→MDO, Mgo→MGO, Ulsmgo→ULSMGO2020 (FAL50 Fuel type 목록 검증 통과) |

S03에서 GHG AI Agent 단독으로는 매핑 2~3/60에 그쳤던 원인(코드북 1:N 42필드, 후보집합 18개 제한)을 위 규칙으로 해소했다. 규칙은 `verification/adapters/gears_voyage_transform.py`에 코드로 고정되어 재현 가능하다.

## 3. ② GEARs Type1 Voyage Template 변환 결과 (레그 1: PACTB → GTPRQ)
| Type1 열 | 값 | 도출 근거 |
|---|---|---|
| Voyage No. / Port code (DEP→ARR) | 1 / PACTB → GTPRQ | IMO0191 / IMO0111 · IMO0108 |
| Departure / Arrival (UTC) | 2026-04-19 20:36 / 2026-04-25 01:00 | DEPARTURE_SBY(IMO0065) / ARRIVAL(IMO0063) |
| Time spent at sea / Distance travelled | 124.4 h / 871.6 nm | ATA−ATD / Σ IMO0613(steamingDistanceSlr) |
| HFO ROB dep / arr, Consumption, Bunkered | 298.69 / 841.90 / 54.96 / 599.97 MT | VLSFO2020 계열 → HFO 열 (FAL50: "HFO w/ S 0.1~0.5%") |
| MGO ROB dep / arr, Consumption, Bunkered | 115.98 / 202.26 / 0.60 / 88.30 MT | MGO+ULSMGO2020 → MGO 열 |
| Cargo operation (ARR) | Yes | 도착 후 CARGO_WORK 이벤트 |
| Cargo operation (DEP) · Idle at anchorage · Cargo carried | **미도출** | Provider 이벤트에 항목 없음 |

레그 2(GTPRQ 출항 2026-04-29 12:42, 337 nm 진행 중)는 도착 이벤트가 없어 미완료 레그로 기록했다.

## 4. ③ Nexawave API 데이터 리스트 (Post DCS/MRV Voyage Template)
| 항목 | 결과 |
|---|---|
| 필드 대응 | Type1 열 → API 속성 1:1 (VoyageNo, PortCodeDep, HfoDepart, BerthHfoConsump, BdvHfo …) 132 필드 중 사용 69(레그 1 값 있음 63) |
| 필수 52 필드 충족 (레그 1) | **50 / 52** — 미충족 DepartureCargoOperYn, TotalIdleSpentTime |
| 형식 | DepartureDate YYYY-MM-DD, DepartureTime HH:MM, Yes/No 적합. **ImoNo 7자리 위반**(테스트 선박 8자리) |
| 헤더 가정 | DataVerifYear 2026, VerificationTypeCode 002(IMO DCS) — EU MRV(001) 병행 여부 결정 필요 |
| 전송 | 미실행. Token 미보유, endpoint URL 상세 페이지에 미노출. 산출물 `kr-systems-api-datalist.json` |

## 5. 검증 판정 — **PARTIAL**
| 검사 | 건수 | 내용 |
|---|---|---|
| 템플릿 규칙 검사 | 53 | FAIL 6 · WARNING 5 · 미완료 레그 6 · PASS 36 |
| FAIL (필수 미도출) | 6 | 출항 화물작업 여부, 정박 유휴시간, MRV 화물량(승객/중량) ×2행 |
| WARNING | 5 | MGO 질량수지 +1.42 MT(허용 ±1.01), 거리 교차(Σ항주 871.6 vs ΔdistanceToGo 969.6), 정박 중 ROB 감소 HFO 19.07·MGO 0.8 MT 미보고, PACTB 템플릿 UNLOCODE 시트 미수록 |
| 질량수지 HFO | 통과 | 298.69 + 599.97 − 54.96 − 841.90 = +1.80 MT (허용 ±4.21) |
| 재현성 | 확보 | 입력 sha256·코드북·FAL50 registry(elementCount 1205)·스크립트 고정, 재실행 동일 |

판정 근거: 전달(IDS)·표준 매핑·GEARs 구조 변환은 재현 가능하게 성립(PASS 요건). 그러나 Provider 이벤트 데이터만으로는 DCS/MRV 필수 항목 4종을 채울 수 없고, 정박 소비량이 이벤트에 보고되지 않아 제출 가능 데이터로는 미완성 → PARTIAL.

## 6. 조치 요청 및 결정 사항
| 대상 | 조치 |
|---|---|
| 랩오투원(vessellink) | ① FAL50 Event type 코드(EV01/02/10/16) 채택, 벙커링·하역은 Operation type 병기 ② 출항 화물작업 여부·정박(앵커) 시작/종료 이벤트·화물량(IMO Compendium 화물 요소) 추가 ③ CARGO_WORK 등 정박 이벤트에 연료 소비량 보고 ④ 결측 표기 −9999/"" 정리 ⑤ 코드북 1:N 항목(42/68)에 컨텍스트 규칙 명시 |
| KR GEARs / Nexawave | ① Voyage Template API endpoint URL·Token 발급 ② 템플릿 UNLOCODE 시트에 PACTB 등 누락 항구 갱신 ③ 테스트 선박용 IMO No 정책 |
| KR 결정(D6~D8) | D6 VLSFO/ULSFO → HFO 열 분류 승인(FAL50 코드 설명 근거) D7 VerificationTypeCode 002 단독/001 병행 D8 본 어댑터 규칙을 GHG AI Agent 후보집합·ingress 에 반영(D2·D4 연계) |

증적: `verification/evidence/C02/manual_S04/` (gears-transform/*, kr-systems-api/voyage_template_fields.json, reference/*)
