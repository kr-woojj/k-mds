---
paths:
  - "shared/standard-model/**"
  - "ontology/**"
  - "apps/imo-compendium-mapping-validator/**"
---
# 표준 모델·온톨로지

- 기본 틀은 7개 데이터 그룹: Ship, Voyage, Weather, Cargo, ROB, Fuel Consumption, Power Consumption.
- 항목마다 기록한다: IMO Compendium 데이터 요소(IMO번호) / ISO 19848 채널 / 단위 / 형식(예: n..5) /
  제도별 필수 여부(IMO DCS, CII, EU MRV, UK MRV) / 집계 주기(정오, 이벤트, 항차) / 출처(센서, 수기).
- 스키마를 바꾸면 같은 커밋에서 OpenAPI 명세, 예제 페이로드, 검증 스킬의 기대값을 함께 고친다.
- 하위 호환이 깨지는 변경은 버전을 올리고 `CHANGELOG.md`에 적는다. 앱 2종이 이 스키마를 읽는다.
- FuelEU Maritime, IMO 넷제로 프레임워크 항목은 계획서 범위 밖이다. 추가할 때 `x-scope: extension`으로 표시한다.
