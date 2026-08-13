# Changelog

이 프로젝트의 주요 변경 사항을 기록한다. [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따른다.

## [Unreleased]

### Added

- Skill 책임 분리(ADR-0002) — 기존 구조 검사를 `schema_contract_check`로 이동하고, `schema_validate`는 Pydantic SSOT 기반 실제 Payload 검증(`normalizedPayload` 반환, 원본 값 비노출)으로 변경, Contract Test 37건 (2026-08-13)
- Cross-platform Schema Drift EOL 정책 — `.gitattributes`에 `schemas/generated/*.schema.json text eol=lf`를 추가하여 Windows fresh clone에서도 byte 단위 Drift 검사가 동일하게 동작 (2026-08-13)
- Schema Drift Gate `scripts/check_schema_drift.py` + `dev.py check-schemas` — Pydantic 모델과 committed generated Schema의 byte 단위 불일치를 Local·CI validate에서 차단, Drift Test 10건 (2026-08-13)
- 첫 결정론적 Skill `schema_validate` (`src/k_mds/skills`) — 생성된 JSON Schema의 최소 Contract(camelCase/snake_case alias 정책 포함)를 검증하고 항상 `SkillResult` 반환, 예외 미전파·LLM 미사용, Contract Test 16건 (2026-08-12)
- Schema Generator `scripts/generate_schemas.py` — `src/k_mds/models`에서 `schemas/generated/{ontology,validation}.schema.json` 결정론적 생성 (UTF-8, sort_keys, timestamp 없음), ADR-0001로 Pydantic SSOT를 `src/k_mds/models`로 확정, Contract Test 11건 (2026-08-12)
- Pydantic Core Contract `src/k_mds/models` (Single Source of Truth) (2026-08-12)
  - Ontology 모델: `Dataset`, `Component`, `DataElement`, `ElementOccurrence`(분리 관리), `CodeList`, `BusinessRule`, `GovernanceStatus`
  - 검증 Contract: `Evidence`, `ValidationFinding`, `SkillResult`, `ResultStatus`, `FindingSeverity`, `DataClassification`, `FINDING_VALUE_POLICY`(정책 선언만, 마스킹 미구현)
  - `model_validator`로 PASS/WARNING/FAIL 상태 불변조건, Severity 분리, Evidence 참조 무결성·중복 금지, Technical Position 미확인 Occurrence의 approved 금지 강제
  - TDD Contract Test 19건 추가 — 상태 불변조건, Evidence 무결성, camelCase 직렬화 (runtime 의존성 pydantic>=2.7)
- `NOTICE.md`: 과제 사사(RS-2024-00454634), IMO Compendium 권리 고지, 제3자 명칭·상표 고지 및 MIT License 적용범위 명시 (2026-08-12)
- `LICENSE.md`: MIT License, Copyright (c) 2026 Korean Register (KR) (2026-08-12)
- Cross-platform 검증 인터페이스 `scripts/dev.py` (setup/build/validate/test/run-mcp) — Makefile, VSCode Task, CI 공용 단일 진입점 (2026-08-12)
  - `.github/workflows/ci.yml`: Python 3.11 + uv, `uv sync --locked` 후 dev.py build/validate 실행
  - `.python-version` 3.11 고정, `requires-python >=3.11,<3.14`
  - Manifest 검증을 PyYAML 구조 검증으로 대체, 재귀 sha256 Key 부재 및 Legacy 명칭 부재 자동 Test 추가
  - `run-mcp`는 미구현 안내 후 exit 2, 데이터 파이프라인 Make Target은 exit 1 정책 유지
- Repository Bootstrap: AGENTS.md §3 기준 최소 실행 가능 Python 프로젝트 Scaffold (2026-08-12)
  - `src/k_mds` 패키지 루트 및 uv 기반 `pyproject.toml` (Ruff, MyPy strict, Pytest)
  - 경계 폴더 Local AGENTS.md (`data/`, `ontology/`, `schemas/`, `src/`, `tests/`)
  - Generated 폴더 직접 수정 금지 안내 (`DO_NOT_EDIT.md`)
  - `data/raw/FAL50/source-manifest.yaml` (`status: pending_source`, 공식 원본 미배치)
  - Makefile 표준 명령 인터페이스 (미구현 Target은 안내 후 exit 1)
  - `.vscode/tasks.json`, `.github/copilot-instructions.md`
  - Bootstrap 범위 Smoke Test

### Changed

- `tests/AGENTS.md`: `data/raw/` 파싱 금지 규칙을 공식 원본(Excel, HTML, PDF)으로 명확화 — Repository 관리 Metadata(`source-manifest.yaml`) 구조 검증은 허용 (2026-08-12)
