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

## 실선 샘플 데이터 실증에서 드러난 갭 (2026-11-17, verification/progress.md S12)

- Provider 필드 `bunkeringStopLtc`, `remark`: 코드북에 후보가 여럿(1:N)이라 좁히지 못해 미매핑이었다. FAL50 registry 재확인 후 최특정 요소로 매핑(에이전트 `lab021_ingress.PICK`, 사람 검토 대상).
  - `bunkeringStopLtc` → IMO0656 Bunker delivery date time (정의 "the time when all fuel has been received"). 탈락 후보 IMO0757 은 BDN 발행일. 값이 현지시각(오프셋 없음)인 점은 남는 갭.
  - `remark` → IMO0606 Voyage leg remarks (Noon Data Report 의 Performance Report 하위). 탈락 후보 IMO0604(항차 단위)·IMO0358(기상)·IMO0196·IMO0764(다른 서식).
- Provider 필드 `isEuPort`: FAL50 registry 에 EU 항만 여부를 나타내는 요소 없음(명칭·정의에 EU/European/MRV 검색 0건) → 갭 확정. UN/LOCODE 국가코드에서 파생하는 규칙으로 다룰지 결정 필요.
- `WeatherDetails.seaHeight`(IMO0632)·`swellHeight`(IMO0635): FAL50 format 이 둘 다 `n..2`(정수 2자리, m). 표준모델 DB 의 정수형은 참조모델과 일치한다. Provider 가 소수(1.5 m 등)로 보내 저장 시 절삭되는 것은 **Provider 정밀도 > 표준 형식**의 갭이다(G-5 재분류). DB 형을 실수로 바꾸면 표준 형식에서 벗어난다 — 사용자 결정 대기. 참고: 검증 스킬이 `n..2` 요소의 소수 값을 PASS 로 판정함(형식 검사 느슨, 확인 필요).
- (2026-11-17 저녁 갱신) 표준 모델 1.1.0 에서 `PerformanceReport.voyage_leg_remarks`(IMO0606)를 추가하고, 벙커 수급 요소 IMO0656·0666·0667 을 FuelConsumption 의 `_BUNKER` 행으로 전달하게 했다(G-6: Provider 벙커링 이벤트에 수급 연료 종류가 없어 연료 행에 붙이지 못함 — WORKAROUND). 이로써 대상 없는 요소는 19종 → 15종(IMO0064, 0066, 0084, 0085, 0109, 0112, 0139, 0143, 0148, 0172, 0452, 0540, 0543, 0580, 0766). 아래 줄은 변경 전 기록.
- 연차보고의 보고 연도: FAL50 registry 에 보고 연도·보고 기간을 나타내는 데이터 요소 없음(명칭·정의 year/period/calendar 검색) → `YearPerformanceReport.report_year` 를 K-MDS 확장 필드로 추가(`x-scope: extension`, IMO 번호 없음). 연도는 보고시각(UTC) 기준으로 나눈다.
- 파고·너울 저장형 결정(2026-11-17, 사용자): IMO Compendium 기준 우선 — 정수 `n..2` 유지, DB 변경 없음.
- Ship-ODMS 전달 경로에 대상이 없는 요소 19종: IMO0064, IMO0066, IMO0084, IMO0085, IMO0109, IMO0112, IMO0139, IMO0143, IMO0148, IMO0172, IMO0452, IMO0540, IMO0543, IMO0580, IMO0606, IMO0656, IMO0666, IMO0667, IMO0766 (run 의 no_target_elements). 이 중 IMO0656·0666·0667 은 openapi.yaml 의 FuelConsumption 에 필드가 있으나 전달 어댑터가 벙커 구조를 채우지 않아 미전달, IMO0606 은 openapi.yaml 에 필드 없음.
