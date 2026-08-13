# Changelog

이 프로젝트의 주요 변경 사항을 기록한다. [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따른다.

## [Unreleased]

### Added

- Normalizer Authorization Gate 통합(ADR-0009/0010 Amendment) — `normalize_compendium`이 Authorization·OutputRootBinding을 필수 입력으로 요구하고 Validator 필수 Flag 6종 전부 승인 시에만 Workbook을 열며, Mapping Sheet의 authorizedSheetOrdinals 포함·headerRow 일치를 강제, medium Confidence Boolean 우회 Option 폐기, Repository Root 결정론 탐지, Synthetic Test 46건으로 재구성 (2026-08-13)
- Normalization Authorization Contract(ADR-0010) — Sheet별 Classification·Header 승인·Finding 처분(blocking/reviewable, Unknown은 기본 blocking)·Logical Output Root를 명시하는 `NormalizationAuthorization` Public Model과 결정론적 Validator, validation.schema.json 재생성, Synthetic Test 47건 (Actual Authorization은 Restricted Artifact로 별도 관리) (2026-08-13)
- Restricted Normalizer(ADR-0009) — `scripts/normalize_compendium.py`: verified Manifest·Inspection Gate(normalizationReady 필수, Override 없음), Generic Mapping Spec Contract, Type Normalization(문자열·수·정수·불리언·날짜), Restricted 출력경로 Boundary와 Atomic Write, Synthetic Test 48건 (실제 FAL50 변환은 별도 승인 작업) (2026-08-13)
- Derived Data 공개 정책(ADR-0008) — IMO 파생 Normalize 산출물을 internal-restricted로 분류(공개 권한 미확인에 따른 Default Deny), `data/normalized` 생성물을 Git에서 기본 제외, 공개는 별도 승인과 별도 ADR 필요, Ignore 정책 Regression Test 5건 (2026-08-13)
- Fail-closed Workbook Inspector(ADR-0007) — `scripts/inspect_excel.py`: Manifest Gate(verified/pending/invalid), ZIP Container Preflight(Macro·External Link·Embedded·ActiveX 기본 Fatal), read-only Structure/Header Digest Inventory, 결정론적 JSON Report(원문·이름·경로·Hash 비저장), Synthetic Fixture Test 50건 (runtime 의존성 openpyxl) (2026-08-13)
- Source Manifest Loader(ADR-0006) — `source_manifest_load` Skill: Manifest 선언 SHA-256과 실제 파일 Hash의 Chunk 단위 검증, verified/status 입력 금지(Loader가 결정), 경로 이탈·Symlink 차단, `SourceManifest` 모델과 `source_hash` 64자 lowercase hex pattern 강제(runtime 의존성 PyYAML), Test 42건 (2026-08-13)
- Final Governance Result Assembler(ADR-0005) — `governance_assemble` Skill: 명시된 Decision 정보와 evidence_build 결과만으로 GovernanceResult 조립(상태 비추론, Evidence dedup·충돌 검출, 실행 성공과 Decision 분리), Contract Test 41건 (2026-08-13)
- Result Classification Contract(ADR-0004) — Evidence 최소 1개가 필수인 `GovernanceResult`(APPROVED/REVIEW_REQUIRED/REJECTED 불변조건, camelCase Contract)를 SkillResult와 분리 정의, validation.schema.json 재생성, Test 21건 (2026-08-13)
- Evidence Provenance Contract(ADR-0003) — `SourceManifestEntry` 모델(verified·approved 불변조건, 상대경로 강제)과 결정론적 `evidence_build` Skill(`evidence:<source_id>`, Hash 미계산·원본 값 비노출), ontology.schema.json 재생성, Test 23건 (2026-08-13)
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

### Fixed

- Normalization Authorization Binding 보강(ADR-0010 Amendment) — Report 원 Byte SHA-256 Identity 결합, 전체 Sheet Coverage·Finding 집합 정확 일치, 현재 Report의 Blocking Finding 자기선언(resolved) 금지, Controlled Reason Code Pattern, `OutputRootBinding` Model과 Restricted 출력 경로 검증, Test 72건으로 확장 (2026-08-13)
- Workbook Inspector Hardening(ADR-0007 Amendment) — `data/.gitignore`로 raw Restricted Artifact 차단, `--source-base-dir` 지원(Repository 외부 Local Restricted Manifest 검증), Strict pending Placeholder Contract 판별, XML Read Limit Skip Finding, External Link Metric 분리, Test 18건 추가 (2026-08-13)
- `source_manifest_load` Manifest Parsing 보강(ADR-0006 Amendment) — YAML 중복 Key 거부(`MANIFEST_DUPLICATE_KEY`), Entry Contract·Hash Format을 파일 I/O 전에 검증, `SOURCE_HASH_FORMAT_INVALID`와 `SOURCE_HASH_MISMATCH` 분리, Test 23건 추가 (2026-08-13)
- `schema_validate`·`schema_contract_check` Runtime 입력 경계 보강 — 비문자열 model_name/schema_name(None·list·dict·int)에서 예외를 전파하지 않고 `MODEL_NAME_NOT_STRING`/`SCHEMA_NAME_NOT_STRING` Finding의 SkillResult FAIL 반환, 입력값 비노출 (2026-08-13)
- `evidence_build` Runtime 입력 경계 보강 — str·None·list·int·임의 객체 입력에서 예외를 전파하지 않고 `SOURCE_ENTRY_NOT_OBJECT` Finding의 SkillResult FAIL 반환, 입력값 비노출 (2026-08-13)

### Changed

- `tests/AGENTS.md`: `data/raw/` 파싱 금지 규칙을 공식 원본(Excel, HTML, PDF)으로 명확화 — Repository 관리 Metadata(`source-manifest.yaml`) 구조 검증은 허용 (2026-08-12)
