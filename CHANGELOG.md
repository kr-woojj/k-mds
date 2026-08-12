# Changelog

이 프로젝트의 주요 변경 사항을 기록한다. [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따른다.

## [Unreleased]

### Added

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
