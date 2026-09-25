# S-1-1 실증 자동화 결과 — run_04

- 판정: **PARTIAL**
- 실행: 2026-09-25T17:25:49.744520+00:00 / 오케스트레이터 n8n 실행 로그: http://localhost:5678/workflow/Pycuq2NaVtsIv3xJ/executions/4
- LLM: {"status": "READY", "provider": "gemini", "real": true} / 코드 commit 4ee4e3847166f100bb4e575af00d799e0d9fc50a (dirty=True)
- 원본 payload: `/work/verification/evidence/C02/manual_S03/step-04/payloads/Noon_Report_API__e5e3be7e7a31.json` sha256 fb23ffbdcb00e11d7378ea390728bf895025196713413db5758f0e674bb998b0
- 판정 기준: 시나리오 v0.2 §3 (ISO/IEC DIS 25023:2014(E)), M4 ≥ 0.95 채택

## 측정치 (ISO/IEC 25023)

| 측정 | 25023 | X | A | B |
|---|---|---|---|---|
| M1 | CIn-2-G 취지(전달 정확성) | N/A |  |  |
| M2 | FCp-1-G 매핑 완결성 | 0.9394 | A_unmapped=44 | B_source_fields=726 |
| M3 | FCr-1-G 검증 정확성 | 1.0 | A_validation_fail=0 | B_mapped_fields=682 |
| M4 | FCr-1-G 필드 단위 값 정합성(채택 정합율) | 0.9872 | A_mismatch=4 | B_fields_with_target=313 |
| M5 | CIn-1-G 취지(필수 요소) | N/A |  |  |

## 판정 규칙

| 규칙 | 결과 |
|---|---|
| R-M4 정합율 ≥ 0.95 | PASS |
| R-M3 검증 정확성 = 1.0 | PASS |
| R-M2 매핑 완결성 ≥ 0.95 | FAIL |
| R-T6 Ship-ODMS HTTP 오류 0 | PASS |
| R-T5 에이전트 evidence 무결성 | PASS |
| R-T2 IDS 전달(수행 시) | FAIL |
| R-T8 재현성(직전 run 과 M2·M3·M4 동일) | FAIL |

## 단계별 결과

- T0 baseline: Ship-ODMS reachable=True, 후보집합 0.2.0-provisional(159)
- T2 IDS 전달: DIFFERENT — 다르면 Provider 스냅샷이 바뀐 것(F-22 참조). 시험은 --source 본으로 계속 진행.
- T3~T5 에이전트: 이벤트 12건, 증적 무결성 OK, HTTP 오류 0건
- T6 Ship-ODMS 전송: {"ship": 9, "voyage": 8, "port_calls": 2, "reports": 12, "calls": 16}, 오류 0건 (UI http://localhost:3030)
- T7 정합성: 대조 313건 중 불일치 4건, 표준모델 대상 없음 요소 14개
- T8 재현성(직전 run run_03): {"M2": false, "M3": true, "M4": false}

## 이벤트별 에이전트 결과

| # | correlation_id | event | HTTP | status | fields | unmapped | LLM 호출 | PASS/WARN/FAIL | 무결성 |
|---|---|---|---|---|---|---|---|---|---|
| 0 | S11-RUN_04-LAB021-NOON-00000009-000 | DEPARTURE_SBY | 200 | REVIEW_REQUIRED | 65 | 1 | 1 | 65/17/0 | OK |
| 1 | S11-RUN_04-LAB021-NOON-00000009-001 | BUNKERING | 200 | REVIEW_REQUIRED | 27 | 2 | 1 | 1/3/0 | OK |
| 2 | S11-RUN_04-LAB021-NOON-00000009-002 | RUP | 200 | REVIEW_REQUIRED | 57 | 0 | 0 | 58/15/0 | OK |
| 3 | S11-RUN_04-LAB021-NOON-00000009-003 | NOON_AT_SEA | 200 | REVIEW_REQUIRED | 72 | 0 | 0 | 73/22/0 | OK |
| 4 | S11-RUN_04-LAB021-NOON-00000009-004 | NOON_AT_SEA | 200 | REVIEW_REQUIRED | 72 | 0 | 0 | 73/22/0 | OK |
| 5 | S11-RUN_04-LAB021-NOON-00000009-005 | NOON_AT_SEA | 200 | REVIEW_REQUIRED | 72 | 6 | 0 | 67/21/0 | OK |
| 6 | S11-RUN_04-LAB021-NOON-00000009-006 | ARRIVAL | 200 | REVIEW_REQUIRED | 68 | 6 | 1 | 63/14/0 | OK |
| 7 | S11-RUN_04-LAB021-NOON-00000009-007 | CARGO_WORK | 200 | REVIEW_REQUIRED | 27 | 4 | 0 | 23/3/1 | OK |
| 8 | S11-RUN_04-LAB021-NOON-00000009-008 | DEPARTURE_SBY | 200 | REVIEW_REQUIRED | 65 | 6 | 1 | 60/15/0 | OK |
| 9 | S11-RUN_04-LAB021-NOON-00000009-009 | RUP | 200 | REVIEW_REQUIRED | 57 | 2 | 0 | 56/15/0 | OK |
| 10 | S11-RUN_04-LAB021-NOON-00000009-010 | NOON_AT_SEA | 200 | REVIEW_REQUIRED | 72 | 7 | 0 | 66/19/0 | OK |
| 11 | S11-RUN_04-LAB021-NOON-00000009-011 | NOON_AT_SEA | 200 | REVIEW_REQUIRED | 72 | 10 | 0 | 63/20/0 | OK |

## M4 불일치 목록 (G-5: Ship-ODMS 정수형 절삭 등)

| cid | IMO | target | source | stored |
|---|---|---|---|---|
| S11-RUN_04-LAB021-NOON-00000009-003 | IMO0632 | WeatherDetails.seaHeight | 0.5 | 0 |
| S11-RUN_04-LAB021-NOON-00000009-004 | IMO0632 | WeatherDetails.seaHeight | 0.5 | 0 |
| S11-RUN_04-LAB021-NOON-00000009-005 | IMO0632 | WeatherDetails.seaHeight | 0.5 | 0 |
| S11-RUN_04-LAB021-NOON-00000009-011 | IMO0632 | WeatherDetails.seaHeight | 0.5 | 0 |

## T2 수신 아티팩트 (원본과 다름 — F-22 Provider 스냅샷 변경)

- 수신 274 B sha256 e243240f85272ff7d039da9e7ceaf5565f6809566b0bb43e7dbbf1ec40abdf55 / 원본 sha256 fb23ffbdcb00e11d7378ea390728bf895025196713413db5758f0e674bb998b0
```
{"code":200,"message":"OK","data":{"general":{"callsign":"TBD09","flag":"","grossTonnage":-9999.0,"imoNo":"00000009","shipName":"TEST_BULK_DIESEL_09","netTonnage":-9999.0,"portOfRegistry":"","subShipType":"NONE","mmsi":0,"masterName":"-9999"},"events":[],"nextCursor":null}}
```

## 증적 파일 (sha256)

- `T0-baseline.json` 58d1f919762734919d3c064f47755c90a2db5692bbd699ad62eae34eacaf79e1
- `T2-ids-transfer.json` 491cac5a7df8a1edd08db5c6b19bc4cea55adabb5809f3f11d0a9f22a0836cd4
- `T3-T5-agent.json` 71d256a35dbb61d082e4d34c757c4ae11c0575cf279bcbff37a9a48ddf83d500
- `shipodms/shipodms-delivery.json` bfc5f19d67a4024abea8073d73e1e62c2c278d59ac30273a79c3bd6a9aa7669e
- `shipodms/consistency-report.json` 88fd4793504483923c551524ff5e1dfd76d2e5e7e7009d3e3a4108e409b2e162
- `result.json` 55be8b4c7d5e8bbcffffa5910d0b64ec8ef900149677435dbef3f0d4db27658b

증적 디렉터리: `/work/verification/evidence/C02/s11/run_04` (덮어쓰기 금지, run 번호 증가) — 생성 2026-09-25T17:28:34.525292+00:00
