
# Ship-ODMS FastAPI Backend

IMO Compendium 기반 선박 운항 데이터 관리 시스템(Ship-ODMS) 백엔드입니다. PRD/ERD/OpenAPI 명세에 따라 설계되었으며, FastAPI와 SQLite를 사용합니다.

---

## 📁 프로젝트 구조

```
python/
├── main.py           # FastAPI 엔트리포인트 및 모든 엔드포인트 구현
├── models.py         # Pydantic 데이터 모델 (OpenAPI/ERD 기반)
├── database.py       # DB 연결 및 초기화 로직 (SQLite)
(openapi.yaml 은 k-mds/shared/standard-model/ 로 이동, 단일 원본)
├── README.md         # 프로젝트 설명서
└── ship_odms.db      # SQLite DB (실행 시 자동 생성)
```

## 🚀 실행 방법

1. 의존성 설치 (가상환경 권장)
	```bash
	pip install fastapi uvicorn pydantic
	```
2. 서버 실행
	```bash
	uvicorn main:app --reload
	```
3. Swagger UI (API 문서): [http://localhost:8000/docs](http://localhost:8000/docs)

## 🗂️ 주요 파일 설명

- **main.py**: 모든 REST API 엔드포인트 구현, DB 연결, 예외처리, OpenAPI 문서 제공
- **models.py**: Ship, YearPerformanceReport, Voyage, PortCall 등 모든 데이터 모델 정의 (Pydantic)
- **database.py**: SQLite DB 연결 및 테이블/스키마 자동 생성 (ERD 기반)
- **../../../shared/standard-model/openapi.yaml**: 공식 OpenAPI 3.0.1 명세 (엔드포인트/스키마 기준, 단일 원본)

## 🛠️ 데이터베이스 초기화

서버 최초 실행 시 `ship_odms.db`가 자동 생성되고, 모든 테이블/관계가 ERD에 맞게 초기화됩니다.
테스트/개발 중 DB를 초기화하려면 `database.py`의 `init_db()`를 직접 실행하거나 서버를 재시작하세요.

## 📑 주요 엔드포인트 예시

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET    | /api/ships | 선박 목록 조회 |
| POST   | /api/ships | 선박 등록 |
| GET    | /api/ships/{ship_id} | 특정 선박 상세 조회 |
| GET    | /api/ships/{ship_id}/year-performance-reports | 연간 성능보고서 목록 |
| POST   | /api/ships/{ship_id}/year-performance-reports | 연간 성능보고서 등록 |
| ...    | ...  | (Voyage, PortCall, PerformanceReport 등 모든 리소스 지원) |

자세한 스키마/파라미터/응답 예시는 Swagger UI(/docs) 또는 openapi.yaml 참고.

## 🧑‍💻 개발/확장 가이드

- 모든 모델/엔드포인트는 OpenAPI 및 ERD 기준으로 엄격히 설계됨
- 중첩 객체(성능보고서 등)는 POST/GET 시 자동으로 처리됨
- 예외/에러 응답은 FastAPI 표준 방식(HTTPException) 사용
- DB 스키마/관계는 database.py에서 관리
- 추가 엔드포인트/필드 필요 시 openapi.yaml, models.py, main.py를 함께 수정

## 📝 참고/문서

- [OpenAPI 명세](../../../shared/standard-model/openapi.yaml)
- [Swagger UI](http://localhost:8000/docs)
- [PRD/ERD/요구사항](../product-requirements.md)
- 완성 예제: 원본 저장소 kr-woojj/data-space 의 `complete/python` (통합 시 제외)

---

**면책조항**: 이 문서는 [GitHub Copilot](https://docs.github.com/copilot/about-github-copilot/what-is-github-copilot)에 의해 현지화되었습니다. 실수가 있을 수 있습니다. 잘못된 부분은 [issue](https://github.com/kr-woojj/data-space/issues/new)로 제보해 주세요.
