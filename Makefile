# k-mds 표준 명령 (AGENTS.md §13)
#
# build, validate, test, run-mcp는 scripts/dev.py에 위임한다.
# Makefile, VSCode Task, CI가 동일한 dev.py 로직을 사용한다.
#
# 미구현 Target 정책: 안내 메시지 출력 후 exit 1 (non-zero).
# 가짜 성공(no-op 후 exit 0)을 만들지 않는다.

.PHONY: help setup build validate test run-mcp inspect normalize ontology schemas compare

.DEFAULT_GOAL := help

help:
	@echo "k-mds 표준 명령"
	@echo ""
	@echo "  구현됨:"
	@echo "    make setup      의존성 설치 (uv sync)"
	@echo "    make build      Bytecode Compile + Package Import 검증 (dev.py)"
	@echo "    make validate   Ruff + MyPy + Pytest Quality Gate (dev.py)"
	@echo "    make test       Pytest 실행 (dev.py)"
	@echo ""
	@echo "  미구현 (실행 시 non-zero exit):"
	@echo "    make run-mcp    MCP Server 미구현 안내 후 exit 2"
	@echo "    make inspect / normalize / ontology / schemas / compare  exit 1"

setup:
	uv sync

build:
	uv run python scripts/dev.py build

validate:
	uv run python scripts/dev.py validate

test:
	uv run python scripts/dev.py test

run-mcp:
	uv run python scripts/dev.py run-mcp

inspect:
	@echo "[k-mds] 'inspect'는 아직 구현되지 않았다 (Repository Bootstrap 단계)."
	@echo "[k-mds] 선행 조건: data/raw/FAL50 공식 원본 배치, scripts/inspect_excel.py 구현."
	@exit 1

normalize:
	@echo "[k-mds] 'normalize'는 아직 구현되지 않았다 (Repository Bootstrap 단계)."
	@echo "[k-mds] 선행 조건: data/raw/FAL50 공식 원본 배치, scripts/normalize_compendium.py 구현."
	@exit 1

ontology:
	@echo "[k-mds] 'ontology'는 아직 구현되지 않았다 (Repository Bootstrap 단계)."
	@echo "[k-mds] 선행 조건: data/normalized 생성, scripts/build_ontology.py 구현."
	@exit 1

schemas:
	@echo "[k-mds] 'schemas'는 아직 구현되지 않았다 (Repository Bootstrap 단계)."
	@echo "[k-mds] 선행 조건: schemas/source Pydantic 모델, scripts/generate_schemas.py 구현."
	@exit 1

compare:
	@echo "[k-mds] 'compare'는 아직 구현되지 않았다 (Repository Bootstrap 단계)."
	@echo "[k-mds] 선행 조건: scripts/compare_versions.py 구현. 사용법: make compare FROM=FAL49 TO=FAL50"
	@exit 1
