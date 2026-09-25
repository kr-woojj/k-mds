# S-1-1 실증 자동화 결과 — run_08

- 판정: **PASS (T2 NOT_TESTED — 외부 IDS 단계는 별도 증적으로 보완)**
- 실행: 2026-09-25T18:00:14.344551+00:00 / 오케스트레이터 n8n 실행 로그: http://localhost:5678/workflow/None/executions/13
- LLM: {"status": "READY", "provider": "gemini", "real": true} / 코드 commit b7244926a83827f77f02e5996146bc96e3e8d5b0 (dirty=True)
- 원본 payload: `/work/verification/evidence/C02/manual_S03/step-04/payloads/Noon_Report_API__e5e3be7e7a31.json` sha256 fb23ffbdcb00e11d7378ea390728bf895025196713413db5758f0e674bb998b0
- 판정 기준: 시나리오 v0.2 §3 (ISO/IEC DIS 25023:2014(E)), M4 ≥ 0.95 채택

## 측정치 (ISO/IEC 25023)

| 측정 | 25023 | X | A | B |
|---|---|---|---|---|
| M1 | CIn-2-G 취지(전달 정확성) | N/A |  |  |
| M2 | FCp-1-G 매핑 완결성 | 0.9945 | A_unmapped=4 | B_source_fields=726 |
| M3 | FCr-1-G 검증 정확성 | 1.0 | A_validation_fail=0 | B_mapped_fields=722 |
| M4 | FCr-1-G 필드 단위 값 정합성(채택 정합율) | 0.9854 | A_mismatch=5 | B_fields_with_target=342 |
| M5 | CIn-1-G 취지(필수 요소) | N/A |  |  |

## 판정 규칙

| 규칙 | 결과 |
|---|---|
| R-M4 정합율 ≥ 0.95 | PASS |
| R-M3 검증 정확성 = 1.0 | PASS |
| R-M2 매핑 완결성 ≥ 0.95 | PASS |
| R-T6 Ship-ODMS HTTP 오류 0 | PASS |
| R-T5 에이전트 evidence 무결성 | PASS |
| R-T2 IDS 전달(수행 시) | PASS |

## 단계별 결과

- T0 baseline: Ship-ODMS reachable=True, 후보집합 0.2.0-provisional(159)
- T2 IDS 전달: NOT_TESTED — source=snapshot (2026-09-12 IDS 수신 보관본 사용)
- T3~T5 에이전트: 이벤트 12건, 증적 무결성 OK, HTTP 오류 0건
- T6 Ship-ODMS 전송: {"ship": 9, "voyage": 8, "port_calls": 2, "reports": 12, "calls": 16}, 오류 0건 (UI http://localhost:3030)
- T7 정합성: 대조 342건 중 불일치 5건, 표준모델 대상 없음 요소 16개
- T8 재현성(직전 run run_07): null

## 이벤트별 에이전트 결과

| # | correlation_id | event | HTTP | status | fields | unmapped | LLM 호출 | PASS/WARN/FAIL | 무결성 |
|---|---|---|---|---|---|---|---|---|---|
| 0 | S11-RUN_08-LAB021-NOON-00000009-000 | DEPARTURE_SBY | 200 | REVIEW_REQUIRED | 65 | 1 | 1 | 65/17/0 | OK |
| 1 | S11-RUN_08-LAB021-NOON-00000009-001 | BUNKERING | 200 | REVIEW_REQUIRED | 27 | 1 | 1 | 27/3/0 | OK |
| 2 | S11-RUN_08-LAB021-NOON-00000009-002 | RUP | 200 | REVIEW_REQUIRED | 57 | 0 | 0 | 58/15/0 | OK |
| 3 | S11-RUN_08-LAB021-NOON-00000009-003 | NOON_AT_SEA | 200 | REVIEW_REQUIRED | 72 | 0 | 0 | 73/22/0 | OK |
| 4 | S11-RUN_08-LAB021-NOON-00000009-004 | NOON_AT_SEA | 200 | REVIEW_REQUIRED | 72 | 0 | 0 | 73/22/0 | OK |
| 5 | S11-RUN_08-LAB021-NOON-00000009-005 | NOON_AT_SEA | 200 | REVIEW_REQUIRED | 72 | 0 | 0 | 73/22/0 | OK |
| 6 | S11-RUN_08-LAB021-NOON-00000009-006 | ARRIVAL | 200 | REVIEW_REQUIRED | 68 | 1 | 1 | 68/15/0 | OK |
| 7 | S11-RUN_08-LAB021-NOON-00000009-007 | CARGO_WORK | 200 | REVIEW_REQUIRED | 27 | 0 | 0 | 28/3/0 | OK |
| 8 | S11-RUN_08-LAB021-NOON-00000009-008 | DEPARTURE_SBY | 200 | REVIEW_REQUIRED | 65 | 1 | 1 | 65/17/0 | OK |
| 9 | S11-RUN_08-LAB021-NOON-00000009-009 | RUP | 200 | REVIEW_REQUIRED | 57 | 0 | 0 | 58/15/0 | OK |
| 10 | S11-RUN_08-LAB021-NOON-00000009-010 | NOON_AT_SEA | 200 | REVIEW_REQUIRED | 72 | 0 | 0 | 73/22/0 | OK |
| 11 | S11-RUN_08-LAB021-NOON-00000009-011 | NOON_AT_SEA | 200 | REVIEW_REQUIRED | 72 | 0 | 0 | 73/22/0 | OK |

## M4 불일치 목록 (G-5: Ship-ODMS 정수형 절삭 등)

| cid | IMO | target | source | stored |
|---|---|---|---|---|
| S11-RUN_08-LAB021-NOON-00000009-003 | IMO0632 | WeatherDetails.seaHeight | 0.5 | 0 |
| S11-RUN_08-LAB021-NOON-00000009-004 | IMO0632 | WeatherDetails.seaHeight | 0.5 | 0 |
| S11-RUN_08-LAB021-NOON-00000009-005 | IMO0632 | WeatherDetails.seaHeight | 0.5 | 0 |
| S11-RUN_08-LAB021-NOON-00000009-010 | IMO0632 | WeatherDetails.seaHeight | 0.8 | 0 |
| S11-RUN_08-LAB021-NOON-00000009-011 | IMO0632 | WeatherDetails.seaHeight | 0.5 | 0 |

## 증적 파일 (sha256)

- `T0-baseline.json` 9071a255d05ebd456da646b85df99f7b680c86c458a117c5bad33a3b89e174d8
- `T2-ids-transfer.json` 6c1aa588d48eaa977ad362dcedf035a3de1f14c29fa5e288b88afe14254f1fde
- `T3-T5-agent.json` 3ead3de51bbe5a0ec951cd11c9c13e4934b065ebe6c951f9cb4d5eaa2c951ce0
- `shipodms/shipodms-delivery.json` 360dfb5afdb9461348cc54ef8bbf59cab1add5f45f4169430f60a1fc0c4beaa6
- `shipodms/consistency-report.json` c2f8a5f62344a29f4acce5532d783752ed4a6269c858f6391f0aca7132e66489
- `result.json` d439b9e4b14cd11dfc994cc20e9d2fa00bd7df68273d6a77e9a355e426b98361

증적 디렉터리: `/work/verification/evidence/C02/s11/run_08` (덮어쓰기 금지, run 번호 증가) — 생성 2026-09-25T18:04:41.730570+00:00
