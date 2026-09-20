# K-MDS 폴더 통합 Phase 0 조사 결과 (INVENTORY)

조사일 2026-09-20. 셸 Git Bash(Windows 11). 읽기 전용 조사이며 아무것도 옮기지 않았다.
원본 3개 폴더와 k-mds는 모두 GitHub `kr-woojj/` 공개 저장소다. 커밋은 통합 완료 후 한 번에 한다(사용자 지시).

## 1. 폴더별 조사

| 항목 | k-mds (루트) | imo-compendium-mapping-validator | data-space | kr-ghg-ai-agent |
| --- | --- | --- | --- | --- |
| 경로 | C:\kr-dev\k-mds | C:\kr-dev\imo-compendium-mapping-validator | C:\kr-dev\data-space | C:\kr-dev\kr-ghg-ai-agent |
| git | main, 42 commits, origin 대비 +15 미푸시 | main, 2 commits, 원격과 동일 | main, 29 commits, 원격과 동일 | main, 원격과 동일 |
| 미커밋 | 30 (부트스트랩 적용분, 커밋 보류) | 0 | **30** (untracked 28: java/, dotnet/, javascript/, complete/*, openapi.yaml, compose.yaml 등 앱 본체) | 0 |
| 언어/패키지 | Python 3.11+, uv, hatchling | Python 3.12+, uv | Python(uv)+Java(Gradle)+.NET+JS(npm). 워크숍 저장소(Copilot Vibe 코딩) 위에 Ship-ODMS 앱 | Python 3.12, uv |
| 실행 | `uv run python scripts/dev.py build` | `uv run python -m app.api serve --db registry.sqlite3` | `python/main.py`(FastAPI), `compose.yaml` | `PYTHONPATH=src uv run uvicorn --factory ghg_agent.api.app:create_app` |
| 테스트 | `uv run python scripts/dev.py test` | `uv run pytest -q` | 없음(테스트 폴더 부재) | `uv run pytest` (unit/contract/integration, live_llm 조건부) |
| 테스트 기준선(09-20) | 574 pass / 2 fail / 3 skip → 2건 원인 분석·수정(§5) | 71 pass | 미실행 | unit+contract 47 pass |
| 지침 파일 | CLAUDE.md, AGENTS.md(+ data/ontology/schemas/src/tests 하위 5개), .github/copilot-instructions.md, .claude/ | 없음. **SKILL.md 없음**(`app/skill/`은 Python 모듈) | .github/copilot-instructions.md, docs/custom-instructions/*/copilot-instructions.md 6개(워크숍 자료) | 없음 |
| 비밀값 후보 | `.env.example`만(실값 없음). `*Secretariat*.pdf`는 이름 매칭 오탐 | 없음 | `./.env` | `./.env` (IDS_CONNECTOR_*, LLM 키. 내용 미열람) |
| 10MB 초과 | docs/(RS-2024-00454634)/ 3.5GB (hwpx 136MB 등). `.gitignore`로 제외 완료 | 없음 | 없음(단, java/ 78MB, dotnet/ 21MB, complete/ 88MB는 bin/build/obj 산출물) | 없음. var/ 2.7MB(registry.sqlite3) |
| 목적지 | 루트(현 구조 유지) | `apps/imo-compendium-mapping-validator/` (권장, §3) | `apps/data-space/` | `apps/kr-ghg-ai-agent/` |

k-mds `docs/` 폴더 수준 목록: `(RS-2024-00454634)…/00 공고`, `01 KEIT 접수 연구개발계획서`, `02 KEIT 협약`, `03 연구개발 1차년도(2024)`, `04 2차년도(2025)`, `05 3차년도(2026)`, `06 참고자료(IACS, IAPH, IMO Compendium, ISTS, KDATA, portcalloptimization, K-Model)`, `adr/`, `agent/`. 파일은 열지 않았다.

## 2. 폴더 간 의존 (이동 시 깨질 수 있는 것)

| 의존 | 위치 | 현재 값 | 통합 후 |
| --- | --- | --- | --- |
| ghg-agent → validator | `src/ghg_agent/config.py:47,87`, `.env.example` `IMO_MAPPING_SKILL_PATH` | `PROJECT_ROOT.parent / "imo-compendium-mapping-validator"` (형제 폴더) | validator를 `apps/imo-compendium-mapping-validator/`로 두면 **수정 없이 동작**. 이름을 바꾸면 기본값과 README·주석 6곳 수정 필요 |
| ghg-agent → k-mds FAL50 xlsx | `tools/prepare_registry.py`, `K_MDS_REFERENCE_PATH` | `../k-mds/data/raw/FAL50/IMO Compendium.xlsx` | `apps/` 아래로 가면 `../../data/raw/FAL50/…`. 환경변수로 덮어쓰거나 기본값 수정 |
| ghg-agent → data-space | README §2 참조만 | OpenAPI 참조(read-only) | 영향 없음 |
| validator → 없음 | | | |
| k-mds verification/ → ghg-agent, validator | `verification/run_c02.py`, evidence 경로 | 형제 폴더 절대경로 가능성 | Phase 2 후 run_c02.py 경로 점검 |

## 3. validator 목적지 판단

SKILL.md가 없으므로 스킬 폴더(`.claude/skills/`)가 아니라 `apps/` 아래로 간다. 스킬 문서는 `apps/mapping-validator/`를 예시했지만,
설계서 원칙("앱 폴더 이름은 원본 그대로")과 ghg-agent의 기본 경로 의존(§2)을 고려하면 **`apps/imo-compendium-mapping-validator/`**가 맞다.
채택 시 부트스트랩 때 고친 CLAUDE.md, AGENTS.md, .claude/rules/standard-model.md의 `apps/mapping-validator/` 3곳을 다시 바꾼다.

## 4. 중복 파일 (sha256 기준)

| 종류 | 파일 | 판정 |
| --- | --- | --- |
| OpenAPI (Ship-ODMS) | data-space `openapi.yaml` = `complete/openapi.yaml` = `complete/python/openapi.yaml` (해시 93286072…) | 동일 3벌. 원본 후보 |
| OpenAPI (Java 변형) | `java/ship_odms/openapi_actual.yaml` = `java/ship_odms/src/main/resources/openapi.yaml` (e5b4e5c5…), `complete/java/…/openapi.yaml` (361e25f6…), `openapi_actual.json` | 이름은 같지만 내용 다름. Java 구현 산출물 |
| IMO Compendium.xlsx | k-mds `data/raw/FAL50/` (1.83MB, FAL50, manifest sha256 일치) vs data-space `docs/imo_compendium/` (1.33MB, 2026-03-03) | **버전 다름**. FAL50(k-mds)이 정본. data-space 사본은 Phase 3에서 제거 후보 |
| 코드리스트 | ghg-agent `var/reference/code_lists.json` (45ac3e27…) vs k-mds `verification/evidence/C02/manual_S04/reference/fal50_code_lists.json` (522e4b08…) | 다름. 전자는 실행 산출물, 후자는 증적. 둘 다 표준 모델 원본 아님 |
| JSON Schema | validator `schemas/*.schema.json` 3개, k-mds `schemas/generated/*.schema.json` 2개 | 각각 고유. 용도 다름(API 계약 / 온톨로지) |
| 매핑 표 | k-mds `verification/evidence/**/mapping-result.json` (run_01 = run_02 동일 쌍 8개) | 증적. 표준 모델 아님. 건드리지 않음 |
| **7개 데이터 그룹 스키마** | **어느 폴더에도 파일 없음** | 가장 가까운 것: data-space `python/models.py`(Ship, Voyage, PortCall, WeatherDetails, CargoOnboard, ElectricConsumption, FuelConsumption 등 12 모델)와 `openapi.yaml`, `imo_compendium.md`(ER 다이어그램, IMO번호 주석). Phase 3은 "사본 중 선택"이 아니라 이것을 `shared/standard-model/`의 초안으로 옮기는 작업이 된다 |

## 5. 실패 작업 분석

- `/kmds-consolidate` 인식 실패: 세션이 `C:\kr-dev`에서 열려 k-mds의 `.claude/skills/`를 못 찾음. 스킬 절차를 수동으로 따름. k-mds 폴더에서 세션을 열면 재발하지 않음.
- k-mds 테스트 2건 실패(`test_source_manifest_is_pending_source`, `test_source_manifest_has_no_sha256_key`): 테스트가 부트스트랩 시점의 "원본 미확보" 상태를 고정. S03 커밋 595a974에서 FAL50 원본을 배치하며 manifest가 approved·sha256 포함으로 바뀜. → 테스트를 "approved이면 파일마다 64자리 sha256이 있고, 디스크에 파일이 있으면 해시가 일치" 검사로 교체.

## 6. 승인이 필요한 결정

1. validator 목적지: `apps/imo-compendium-mapping-validator/` (권장) vs `apps/mapping-validator/`.
2. 들여오는 방식: 사용자 지시(단일 커밋)에 따라 **복사**(node_modules, .venv, bin/build/obj, .env, 캐시 제외). `git subtree add`는 폴더마다 커밋을 만들고, data-space는 앱 본체가 untracked라 이력 보존 실익이 없음. 원본 이력은 GitHub 공개 저장소에 남음.
3. data-space 범위: 워크숍 자료(README, docs/custom-instructions, images, complete/)까지 전부 vs Ship-ODMS 앱(python/, openapi.yaml, imo_compendium.md, docs/imo_compendium)만.
4. `.env` 2개(data-space, ghg-agent): 옮기지 않음(원본 폴더에 그대로). 통합 후 `apps/<이름>/.env`는 사용자가 직접 복사.
5. Phase 1 건너뜀 확정: 온톨로지 코드가 이미 `src/`, `ontology/`, `schemas/`에 있고 `verification/`은 그대로 둔다.
