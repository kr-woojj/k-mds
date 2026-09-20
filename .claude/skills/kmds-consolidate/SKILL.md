---
name: kmds-consolidate
description: 흩어진 K-MDS 작업 폴더 4개(k-mds, imo-compendium-mapping-validator, data-space, kr-ghg-ai-agent)를 k-mds 루트 아래 하나의 저장소로 통합한다. 사용자가 /kmds-consolidate 로 호출할 때만 실행한다.
disable-model-invocation: true
argument-hint: "[phase 번호 또는 status]"
---

# K-MDS 폴더 통합

k-mds를 루트로 삼아 나머지 3개 폴더를 옮겨 온다. 단계마다 멈추고 사용자 승인을 받는다.
진행 상태는 `_archive/consolidation/STATE.md`에 기록하고, 세션을 새로 시작하면 이 파일부터 읽어 이어서 한다.
인자가 `status`면 STATE.md만 요약해 보여 주고 끝낸다.

## 절대 규칙
- 원본 폴더 3개는 **복사만 하고 지우지 않는다.** 삭제와 이름 변경은 사용자가 직접 한다.
- 각 단계 전에 k-mds가 git 저장소인지 확인하고, 아니면 Phase 1에서 `git init`을 제안한다.
  단계가 끝날 때마다 커밋해 되돌릴 수 있게 한다. `git push`는 하지 않는다.
- `.env`, 인증서·키(`*.pem`, `*.p12`, `*.key`), 실선·KR-GEARs·IDS 수신 데이터는 읽지도 옮기지도 않는다.
  발견하면 경로만 목록에 적고 사용자에게 어떻게 할지 묻는다.
- 셸을 먼저 확인한다(PowerShell, Git Bash, WSL). 확인된 셸의 문법으로만 명령을 만든다.
- 목표 구조는 루트 `AGENTS.md`의 폴더 지도다. 그와 다르게 배치하고 싶으면 이유를 말하고 묻는다.

## Phase 0. 조사 (읽기만)
1. 사용자에게 원본 폴더 3개의 절대경로를 묻는다. 접근이 안 되면 `/add-dir`로 추가해 달라고 요청한다.
2. 폴더마다 조사한다: git 저장소 여부·브랜치·미커밋 변경·원격, 언어와 패키지 관리자, 실행·테스트 명령,
   용량 큰 파일(10MB 초과), 비밀값 후보 파일의 경로, 자체 CLAUDE.md·AGENTS.md·.claude/ 유무.
3. k-mds도 같은 방식으로 조사한다. `docs/` 하위는 폴더 수준 목록만 만든다. 파일을 열어 읽지 않는다.
4. 중복을 찾는다: 표준 모델 스키마, 코드리스트, OpenAPI 명세, 매핑 표가 여러 폴더에 있는지.
   파일 해시로 같은 파일과 이름만 같은 파일을 구분한다.
5. `imo-compendium-mapping-validator`에 `SKILL.md`가 있는지 본다.
   있으면 목적지는 `.claude/skills/imo-compendium-mapping-validator/`, 없으면 `apps/imo-compendium-mapping-validator/`(원본 이름 유지)이다.
6. 결과를 `_archive/consolidation/INVENTORY.md`로 쓰고 요약을 보여 준다. **멈추고 승인을 받는다.**

## Phase 1. 루트 정비
1. k-mds 루트의 기존 온톨로지 코드를 `ontology/`로 옮기는 계획을 파일 단위 표(현재 경로 → 새 경로)로 보여 준다.
   루트에 남길 것: `AGENTS.md`, `CLAUDE.md`, `README.md`, `.gitignore`, `.claude/`, `docs/`, `pm/`, `verification/`(진행 중 실증 작업), 그리고 `pyproject.toml`이 가리키는 `src/`, `schemas/`, `data/`, `scripts/`, `tests/`.
   2026-09-20 조사 기준으로 온톨로지 코드는 이미 이 구조에 있으므로 Phase 1은 이동 없이 STATE.md에 "건너뜀"으로 기록하고 넘어간다.
2. 승인 후 `git mv`로 옮긴다. 옮긴 뒤 온톨로지의 빌드·테스트를 돌려 경로 참조가 깨졌는지 확인한다.
3. 기존 `docs/`의 구조는 바꾸지 않는다. 정리안이 있으면 INVENTORY.md에 제안으로만 적는다.
4. 커밋: `chore: 루트 정비(ontology 분리)`. **멈춘다.**

## Phase 2. 앱 들여오기 (폴더 하나씩)
순서: imo-compendium-mapping-validator → data-space → kr-ghg-ai-agent (의존 방향의 역순).
1. 원본이 git 저장소이고 미커밋 변경이 없으면 이력을 보존해 들여온다:
   `git subtree add --prefix=<목적지> <원본 절대경로> <브랜치>`
   미커밋 변경이 있으면 사용자에게 먼저 커밋하도록 요청한다. git 저장소가 아니면 복사한다(제외: 절대 규칙의 파일, `node_modules`, `.venv`, 빌드 산출물).
2. 폴더 이름은 원본 그대로 둔다. 패키지 이름이나 import 경로를 바꾸지 않는다.
3. 들여온 폴더에서 설치·테스트를 돌린다. 실패하면 원인이 경로 이동인지 기존 문제인지 구분해 보고한다.
4. 폴더 하나가 끝날 때마다 커밋하고 STATE.md를 갱신한다. **폴더마다 멈춘다.**

## Phase 3. 표준 모델 단일화
1. Phase 0에서 찾은 중복 스키마·코드리스트·OpenAPI 명세를 비교해 어느 것을 원본으로 할지 표로 제안한다.
   내용이 다르면 차이를 항목 단위로 보여 주고 사용자가 고르게 한다. 임의로 합치지 않는다.
2. 승인된 원본을 `shared/standard-model/`로 옮기고, 각 앱이 그 경로를 읽도록 고친다.
3. 앱 3종의 테스트를 모두 돌린다. 커밋. **멈춘다.**

## Phase 4. 지침 정리와 검증
1. 들여온 폴더에 있던 CLAUDE.md·AGENTS.md는 내용을 검토해 앱 고유 사항(빌드·테스트 명령, 주의점)만 남긴
   `apps/<이름>/CLAUDE.md`로 줄인다. 루트와 겹치거나 어긋나는 문장은 지운다.
2. 루트 `AGENTS.md`의 폴더 지도를 실제 구조에 맞게 고친다.
3. 사용자에게 새 세션에서 `/context`를 실행해 Memory files에 `CLAUDE.md`와 `AGENTS.md`가 보이는지 확인하도록 안내한다.
4. 최종 보고: 옮긴 것, 옮기지 않은 것(비밀값·데이터)과 그 원래 위치, 실패한 테스트, 원본 폴더를 지워도 되는 조건.
   원본 폴더는 사용자가 2주 이상 문제없이 쓴 뒤 직접 보관 처리하도록 권한다.
