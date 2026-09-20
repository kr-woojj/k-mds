# 표준 모델 갭 기록

형식: 항목 / 필요한 곳 / 대응 요소 없음의 근거 / 제안. 억지로 붙이지 않고 여기에 남긴다.

## 7개 데이터 그룹 ↔ `data-model.md` 엔티티 대응 (2026-09-20 통합 시점)

| 그룹 | 엔티티 | 비고 |
| --- | --- | --- |
| Ship | SHIP | |
| Voyage | VOYAGE, PORT_CALL | |
| Weather | WEATHER_DETAILS | |
| Cargo | CARGO_ONBOARD | |
| ROB | (별도 엔티티 없음) | FUEL_CONSUMPTION 등의 `*_rob` 필드(IMO0674, IMO0675, IMO0645, IMO0676)로만 존재. 그룹으로 분리할지 미결 |
| Fuel Consumption | FUEL_CONSUMPTION, FOC_FUEL_TYPE, FOC_CONSUMER_TYPE | |
| Power Consumption | ELECTRIC_CONSUMPTION | |
| (그룹 외) | PERFORMANCE_REPORT, YEAR_PERFORMANCE_REPORT, MEASURED_CARBON_DIOXIDE | 계획서 7개 그룹에 없는 엔티티. 유지 근거 확인 필요 |

## 미확정

- 착수자료 8그룹 184항목 vs 연차보고서 7그룹: 어느 것이 현행인지 미확인 (verification/progress.md S01).
- 랩오투원 코드북 128항목 ↔ 표준 모델 항목 수 불일치 (verification_cases.json D1~D5 결정 대기).
- 항목별 ISO 19848 채널 ID, 제도별 필수 여부(IMO DCS/CII/EU MRV/UK MRV), 집계 주기 컬럼은 아직 기록되지 않음.
