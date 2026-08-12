# k-mds

Korea Maritime Data Space — IMO Compendium on Facilitation and Electronic Business 참조모델 기반 해사 데이터 상호운용 플랫폼.

「스마트·자율운항선박-밸류체인 간 데이터 표준개발 및 서비스 설계」 국가연구개발과제의 일환으로 개발한다.

## 현재 상태

**Repository Bootstrap 단계.** 프로젝트 구조와 개발 규약만 존재하며, 데이터 파이프라인·온톨로지·MCP·LangGraph는 아직 구현되지 않았다.

- IMO Compendium 공식 원본은 아직 배치되지 않았다 (`data/raw/FAL50/source-manifest.yaml`의 `status: pending_source` 참조).
- 개발 규약은 Root [AGENTS.md](AGENTS.md)를 Master Contract로 따른다. 경계 폴더(`data/`, `ontology/`, `schemas/`, `src/`, `tests/`)에는 추가 제약을 담은 Local AGENTS.md가 있다.

## 시작하기

요구사항: Python 3.11 (`.python-version`), [uv](https://docs.astral.sh/uv/), GNU Make(선택).

모든 검증 명령은 Cross-platform 단일 진입점 `scripts/dev.py`를 사용한다.
Makefile, VSCode Task, CI가 동일한 dev.py 로직을 호출한다.

```bash
uv sync                                  # 의존성 설치 (= make setup)
uv run python scripts/dev.py build      # Compile + Import 검증 (= make build)
uv run python scripts/dev.py validate   # Ruff + MyPy + Pytest Quality Gate (= make validate)
uv run python scripts/dev.py test       # Pytest (= make test)
uv run python scripts/dev.py run-mcp    # 미구현 안내 후 exit 2 (= make run-mcp)
```

`make inspect / normalize / ontology / schemas / compare` 등 데이터 파이프라인 명령은 아직 구현되지 않았으며 실행 시 안내 후 exit 1을 반환한다. 전체 명령 목록은 `make help`.

## 구조

폴더 구조와 각 폴더의 책임은 [AGENTS.md](AGENTS.md) §3, §4를 참조한다. `data/normalized/`, `ontology/generated/`, `schemas/generated/`는 스크립트 생성물 폴더이며 직접 수정하지 않는다.

## License

[MIT License](LICENSE.md) — Copyright (c) 2026 Korean Register (KR)
