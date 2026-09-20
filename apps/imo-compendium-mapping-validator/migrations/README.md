# migrations/

Registry SQLite 스키마 마이그레이션 디렉터리.

## 규칙

1. 파일명은 `NNNN_설명.sql` (0-padding 4자리) — 파일명 오름차순으로 적용된다.
2. 적용 이력은 `schema_migrations` 테이블에 기록되며 이미 적용된 스크립트는
   건너뛴다 (`app/registry/database.py::apply_migrations`).
3. **Immutable snapshot 원칙**: 마이그레이션은 구조 추가만 허용한다. 기존
   `compendium_version` / `data_element` / `refmodel_occurrence` 데이터의
   UPDATE·DELETE·DROP은 금지한다 (요구사항 5).
4. DDL은 `app/registry/models.py`의 ORM 정의와 1:1로 동기화하고, 불일치는
   테스트에서 검출한다.
5. 마이그레이션은 idempotent하게 작성한다 (`IF NOT EXISTS`).

## 적용 방법

CLI가 실행 시 자동 적용한다:

```text
python -m app.registry import --file <export> --version <V> --db <path>
```
