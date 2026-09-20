# 제품 요구사항 문서 (PRD)

## 제품 제목

IMO Compendium 기반 선박 운항 데이터 관리 서비스(Ship-ODMS, Operational Data Management Service)

## 문서 버전

1.0.0

## 작성자

한국선급 / 연구본부

## 마지막 업데이트

2026-02-27

---

## 1. 개요

이 프로젝트의 목표는 사용자가 데이터를 생성, 조회, 업데이트, 삭제할 수 있는 기본적이면서도 기능적인 선박 운항 데이터 관리 서비스(Ship-ODMS)를 구축하는 것입니다. API 우선 접근 방식을 통해 웹 또는 모바일 프론트엔드의 백엔드로 사용할 수 있도록 합니다. 첨부된 ERD(`../../shared/standard-model/data-model.md`)를 기반으로 RESTful API 아키텍처를 설계하고 **YAML 형식의 OpenAPI 3.0 명세서**를 생성하는 것이 1차 결과물이다.

## 2. 배경

KR은 선급규칙과 국제협약에 따라 생명과 재산 및 환경을 보호하기 위해 조선 및 해양분야에서 세계를 선도하는 종합적 기술 지원 단체입니다. KR의 연구본부는 기존 고객과 잠재 고객에게 조선해운 산업의 디지털 전환을 지원하기 위한 선박 운항 데이터 관리 웹사이트를 런칭하고자 합니다. 첫 번째 MVP로서, 연구본부는 웹사이트를 빠르게 구축하고자 합니다.

## 3. 목표

* 사용자 생성 데이터에 대한 CRUD 작업 제공.
* 교육용 및 MVP 사용 사례를 위한 단순성 유지.
* RESTful API 설계 및 적절한 오류 처리 보장.
* **표준 기반 스키마 설계:** ERD에 정의된 IMO ID(예: IMO0140)를 OpenAPI 스키마의 `description` 필드에 매핑.
* **계층적 API 설계:** Ship -> Voyage -> Performance Report로 이어지는 종속적 데이터 구조를 RESTful URI로 표현.
* **YAML 자동화:** 사람이 읽고 쓰기 편한 OpenAPI YAML 파일 완벽 자동 생성.

## 4. 주요 기능

API 엔드포인트는 리소스의 계층 구조를 반영해야 한다. 일반적인 `/posts` 대신 아래의 도메인 모델을 사용한다.

### 4.1 선박 (Ship) 관리
선박의 정적(Static) 데이터를 관리한다.
* **GET** `/api/ships` : 등록된 선박 목록 조회
* **POST** `/api/ships` : 신규 선박 등록
* **GET** `/api/ships/{shipId}` : 특정 선박의 상세 정보 조회

### 4.2 연차 실적 보고 (Year Performance Report)
특정 선박의 연간 GHG 집계 데이터를 관리한다.
* **GET** `/api/ships/{shipId}/yearly-reports`
* **POST** `/api/ships/{shipId}/yearly-reports`

### 4.3 항해 (Voyage) 및 입출항 (Port Call)
특정 선박에 종속된 항해 정보와, 해당 항해의 입출항 기록을 관리한다.
* **GET** `/api/ships/{shipId}/voyages` : 선박의 항해 이력 조회
* **POST** `/api/ships/{shipId}/voyages` : 새로운 항해 생성 (Trade service identifier 등 포함)
* **POST** `/api/voyages/{voyageId}/port-calls` : 특정 항해의 입출항 기록 추가

### 4.4 운항 성능 보고 (Performance Report)
SVD Noon Report 등 일일 운항 및 이벤트 데이터를 기록한다. (가장 복잡한 페이로드)
* **GET** `/api/voyages/{voyageId}/performance-reports`
* **POST** `/api/voyages/{voyageId}/performance-reports`
  * *비즈니스 규칙:* 이 POST 요청의 Request Body(JSON)에는 하위 엔티티인 기상(`WeatherDetails`), 적재 화물(`CargoOnboard`), 전기 소비(`ElectricConsumption`), 연료 소비(`FuelConsumption`), 탄소 배출(`MeasuredCarbonDioxide`) 데이터가 **중첩된 객체(Nested Objects) 형태로 한 번에 포함**되어야 한다.

## 5. 데이터 스키마 설계 지침 (For OpenAPI Components)
OpenAPI의 `components/schemas` 섹션은 ERD(`../../shared/standard-model/data-model.md`)를 1:1로 반영해야 한다.

1. **스키마 명명 규칙:** ERD의 테이블명(PascalCase 적용, 예: `YearPerformanceReport`, `FuelConsumption`).
2. **속성 매핑:** ERD의 컬럼을 스키마 속성으로 정의.
3. **IMO ID 주석 필수:** OpenAPI YAML의 `description` 필드에 ERD에 명시된 IMO ID와 정의를 반드시 포함할 것.
   ```yaml
   ship_name:
     type: string
     description: "IMO0142: Ship name"

## 6. 사용자 역할 및 권한

* **익명 사용자**
  * 데이터를 읽을 수 있습니다.

* **인증된 사용자 (owner 필드를 통해)**
  * 데이터를 생성, 업데이트, 삭제할 수 있습니다.

## 7. API 계약

* 최소 v3.0.1 사양으로 OpenAPI 문서 정의.
* 표준 HTTP 상태 코드 사용.
  * `200 OK`, `201 Created`, `204 No Content`, `400 Bad Request`, `404 Not Found`, `500 Internal Server Error`
* Content-Type: `application/json`

## 8. 비기능적 요구사항

* **문서화**: API는 Swagger UI를 사용하여 완전히 문서화되어야 합니다.
* **보안**: 전체 인증이 구현되지 않더라도 입력 검증 및 기본 요청 검증.

## 9. 가정 및 종속성

* 이 제품에는 메모리 DB를 사용합니다.
* 파일 업로드 또는 미디어 지원은 포함되지 않습니다.
* 사용자 등록 또는 로그인/인증 플로우는 없습니다.
* 테스트 코드는 필요하지 않습니다.

## 10. 성공 지표

* 모든 API 엔드포인트에 접근 가능하고 문서화된 대로 응답합니다.
* 데이터에 대한 CRUD를 종단 간에 수행할 수 있습니다.
* OpenAPI에서 생성된 명확한 Swagger 문서.

## 11. 범위 외

* 사용자 인증 (OAuth, JWT 등)
* 실시간 업데이트 또는 알림
* 조정 도구 또는 신고 기능
* 멀티미디어 업로드 (이미지, 비디오)

---

**면책조항**: 이 문서는 [GitHub Copilot](https://docs.github.com/copilot/about-github-copilot/what-is-github-copilot)에 의해 현지화되었습니다. 따라서 실수가 포함될 수 있습니다. 부적절하거나 잘못된 번역을 발견하면 [issue](https://github.com/kr-woojj/data-space/issues/new)를 생성해 주세요.
