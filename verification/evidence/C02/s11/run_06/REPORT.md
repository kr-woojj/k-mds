# S-1-1 실증 자동화 결과 — run_06

- 판정: **PARTIAL**
- 실행: 2026-09-25T17:35:35.102427+00:00 / 오케스트레이터 n8n 실행 로그: http://localhost:5678/workflow/Pycuq2NaVtsIv3xJ/executions/6
- LLM: {"status": "READY", "provider": "gemini", "real": true} / 코드 commit 4ee4e3847166f100bb4e575af00d799e0d9fc50a (dirty=True)
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
| R-T2 IDS 전달(수행 시) | FAIL |
| R-T8 재현성(직전 run 과 M2·M3·M4 동일) | PASS |

## 단계별 결과

- T0 baseline: Ship-ODMS reachable=True, 후보집합 0.2.0-provisional(159)
- T2 IDS 전달: DIFFERENT — 다르면 Provider 스냅샷이 바뀐 것(F-22 참조). 시험은 --source 본으로 계속 진행.
- T3~T5 에이전트: 이벤트 12건, 증적 무결성 OK, HTTP 오류 0건
- T6 Ship-ODMS 전송: {"ship": 9, "voyage": 8, "port_calls": 2, "reports": 12, "calls": 16}, 오류 0건 (UI http://localhost:3030)
- T7 정합성: 대조 342건 중 불일치 5건, 표준모델 대상 없음 요소 16개
- T8 재현성(직전 run run_05): {"M2": true, "M3": true, "M4": true}

## 이벤트별 에이전트 결과

| # | correlation_id | event | HTTP | status | fields | unmapped | LLM 호출 | PASS/WARN/FAIL | 무결성 |
|---|---|---|---|---|---|---|---|---|---|
| 0 | S11-RUN_06-LAB021-NOON-00000009-000 | DEPARTURE_SBY | 200 | REVIEW_REQUIRED | 65 | 1 | 1 | 65/17/0 | OK |
| 1 | S11-RUN_06-LAB021-NOON-00000009-001 | BUNKERING | 200 | REVIEW_REQUIRED | 27 | 1 | 1 | 27/3/0 | OK |
| 2 | S11-RUN_06-LAB021-NOON-00000009-002 | RUP | 200 | REVIEW_REQUIRED | 57 | 0 | 0 | 58/15/0 | OK |
| 3 | S11-RUN_06-LAB021-NOON-00000009-003 | NOON_AT_SEA | 200 | REVIEW_REQUIRED | 72 | 0 | 0 | 73/22/0 | OK |
| 4 | S11-RUN_06-LAB021-NOON-00000009-004 | NOON_AT_SEA | 200 | REVIEW_REQUIRED | 72 | 0 | 0 | 73/22/0 | OK |
| 5 | S11-RUN_06-LAB021-NOON-00000009-005 | NOON_AT_SEA | 200 | REVIEW_REQUIRED | 72 | 0 | 0 | 73/22/0 | OK |
| 6 | S11-RUN_06-LAB021-NOON-00000009-006 | ARRIVAL | 200 | REVIEW_REQUIRED | 68 | 1 | 1 | 68/15/0 | OK |
| 7 | S11-RUN_06-LAB021-NOON-00000009-007 | CARGO_WORK | 200 | REVIEW_REQUIRED | 27 | 0 | 0 | 28/3/0 | OK |
| 8 | S11-RUN_06-LAB021-NOON-00000009-008 | DEPARTURE_SBY | 200 | REVIEW_REQUIRED | 65 | 1 | 1 | 65/17/0 | OK |
| 9 | S11-RUN_06-LAB021-NOON-00000009-009 | RUP | 200 | REVIEW_REQUIRED | 57 | 0 | 0 | 58/15/0 | OK |
| 10 | S11-RUN_06-LAB021-NOON-00000009-010 | NOON_AT_SEA | 200 | REVIEW_REQUIRED | 72 | 0 | 0 | 73/22/0 | OK |
| 11 | S11-RUN_06-LAB021-NOON-00000009-011 | NOON_AT_SEA | 200 | REVIEW_REQUIRED | 72 | 0 | 0 | 73/22/0 | OK |

## M4 불일치 목록 (G-5: Ship-ODMS 정수형 절삭 등)

| cid | IMO | target | source | stored |
|---|---|---|---|---|
| S11-RUN_06-LAB021-NOON-00000009-003 | IMO0632 | WeatherDetails.seaHeight | 0.5 | 0 |
| S11-RUN_06-LAB021-NOON-00000009-004 | IMO0632 | WeatherDetails.seaHeight | 0.5 | 0 |
| S11-RUN_06-LAB021-NOON-00000009-005 | IMO0632 | WeatherDetails.seaHeight | 0.5 | 0 |
| S11-RUN_06-LAB021-NOON-00000009-010 | IMO0632 | WeatherDetails.seaHeight | 0.8 | 0 |
| S11-RUN_06-LAB021-NOON-00000009-011 | IMO0632 | WeatherDetails.seaHeight | 0.5 | 0 |

## T2 수신 아티팩트 (원본과 다름 — F-22 Provider 스냅샷 변경)

- 수신 274 B sha256 e243240f85272ff7d039da9e7ceaf5565f6809566b0bb43e7dbbf1ec40abdf55 / 원본 sha256 fb23ffbdcb00e11d7378ea390728bf895025196713413db5758f0e674bb998b0
```
{"code":200,"message":"OK","data":{"general":{"callsign":"TBD09","flag":"","grossTonnage":-9999.0,"imoNo":"00000009","shipName":"TEST_BULK_DIESEL_09","netTonnage":-9999.0,"portOfRegistry":"","subShipType":"NONE","mmsi":0,"masterName":"-9999"},"events":[],"nextCursor":null}}
```

## 증적 파일 (sha256)

- `T0-baseline.json` 410ac0ab5e72769da1d81bd772aed60a05d747dabc8f16a94414a4b402a936db
- `T2-ids-transfer.json` 491cac5a7df8a1edd08db5c6b19bc4cea55adabb5809f3f11d0a9f22a0836cd4
- `T3-T5-agent.json` 3a1d28d26544390ce888036e0085b01697cfe7688f5affb34df59466347cd8a3
- `shipodms/shipodms-delivery.json` 68b5f5b0a1ef9defdb32ce790c20dd23728c66d21d199a532cb441c047e09fc4
- `shipodms/consistency-report.json` e8c3d953b5de7854f4df824a03c17f3ccd312b6ac6855ae7b97e445e6aa2ef74
- `result.json` 722449661f8eb5e98275880ddb46e175ef009089deadade9ce17b3dd6c083676

증적 디렉터리: `/work/verification/evidence/C02/s11/run_06` (덮어쓰기 금지, run 번호 증가) — 생성 2026-09-25T17:38:13.877432+00:00
