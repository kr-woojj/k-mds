# K-MDS 폴더 통합 전략과 AI Agent 지침 파일 설계

기준일 2026-09-19. 대상 도구: VS Code + Claude Code. 함께 제공하는 `k-mds-bootstrap.zip`을 k-mds 루트에 풀면 이 설계가 그대로 적용된다.

## 1. 파일명 결론

**설계서를 통째로 `AGENTS.md`나 `PRD.md`로 저장하지 않는다.** 설계서는 사람이 읽는 설계 기록(아키텍처 결정, 도구 정의, 평가 세트 포함 약 400행)이고, 에이전트가 매 세션 읽어야 하는 것은 그중 일부다. 역할에 따라 네 개로 나눈다.

| 파일 | 역할 | 누가 읽는가 |
| --- | --- | --- |
| `CLAUDE.md` (루트, 9행) | 첫 줄이 `@AGENTS.md`. 그 아래 Claude Code 전용 지시만 | Claude Code가 세션마다 자동 로드 |
| `AGENTS.md` (루트, 46행) | 저장소 지도, 데이터 흐름, 반드시 지킬 규칙, 작업 규칙 | `CLAUDE.md`의 import로 로드. 다른 코딩 에이전트도 이 이름을 읽음 |
| `.claude/agents/kmds-pm.md` | 설계서 §2의 시스템 프롬프트를 Claude Code 서브에이전트로 옮긴 것 | 사업관리 질의 때만 별도 컨텍스트로 실행 |
| `docs/agent/pm-agent-design.md` | 설계서 v0.2 원문 | 사람. 에이전트는 필요할 때만 |

이렇게 나눈 근거 (Claude Code 공식 문서, code.claude.com/docs/en/memory):

- Claude Code는 `CLAUDE.md`를 읽고 `AGENTS.md`는 직접 읽지 않는다. 공식 권장은 `CLAUDE.md` 첫 줄에 `@AGENTS.md`를 두는 것이다. 심볼릭 링크도 되지만 Windows에서는 관리자 권한이나 개발자 모드가 필요하므로 import 방식을 쓴다.
- `CLAUDE.md`는 파일당 200행 이하가 권장이다. 길수록 컨텍스트를 쓰고 지시 준수율이 떨어진다. import로 쪼개도 시작 시 전부 로드되므로 길이는 줄지 않는다. 설계서 전체를 넣으면 코드 작업 중에도 예산·KPI 지침이 매번 실린다.
- 특정 폴더에만 해당하는 지시는 `.claude/rules/`에 `paths:`를 달아 두면 해당 파일을 읽을 때만 로드된다. 절차는 스킬로 두면 호출할 때만 로드된다.
- `PRD.md`는 Claude Code가 특별히 인식하는 이름이 아니다. 제품 요구사항 문서가 필요하면 `docs/` 아래 일반 문서로 둔다.

과제 수치(지표, 예산, 담당)는 `pm/PROJECT_FACTS.md` 한 곳에만 둔다. 서브에이전트가 시작할 때 이 파일을 읽는다. 협약이 변경되면 이 파일만 고치면 된다.

## 2. 통합 폴더 구조

```text
k-mds/                                  ← 루트 (기존 k-mds)
├─ CLAUDE.md                            @AGENTS.md + Claude 전용
├─ AGENTS.md                            저장소 지도와 공통 규칙
├─ .claude/
│  ├─ settings.json                     .env·인증서 읽기, git push, rm -rf 차단
│  ├─ agents/kmds-pm.md                 사업관리 참모 서브에이전트
│  ├─ rules/                            경로별 규칙 4개 (docs, pm, apps, standard-model)
│  └─ skills/
│     ├─ kmds-consolidate/              폴더 통합 절차 (/kmds-consolidate)
│     └─ imo-compendium-mapping-validator/   ← 기존 폴더 2 (SKILL.md가 있을 때)
├─ docs/                                과제 수행 결과 문서 (기존 구조 유지)
│  └─ agent/pm-agent-design.md          프롬프트 설계서 v0.2
├─ pm/                                  사업관리
│  ├─ PROJECT_FACTS.md                  과제 수치의 단일 기준
│  ├─ kpi/performance.csv, output.csv   성능지표 9개 / 성과지표 (초기값: 2차 연차보고서)
│  ├─ budget/  decisions.md  meetings/  drafts/  evidence/
├─ ontology/                            IMO Compendium 온톨로지 (기존 k-mds 루트의 코드)
├─ shared/standard-model/               표준 모델 단일 원본 (스키마, OpenAPI, 코드리스트, gaps.md)
├─ apps/
│  ├─ data-space/                       ← 기존 폴더 3
│  └─ kr-ghg-ai-agent/                  ← 기존 폴더 4
├─ refs/regulations/                    규정·표준 원문
└─ _archive/consolidation/              통합 조사 결과와 진행 상태
```

설계 판단:

- **앱 폴더 이름은 원본 그대로 둔다.** 이름을 바꾸면 패키지명과 import 경로가 깨진다. 통합의 목적은 위치를 모으는 것이지 리팩터링이 아니다.
- **표준 모델은 `shared/standard-model/`에 한 벌만 둔다.** validator, data-space, ghg-agent가 모두 같은 7개 데이터 그룹 스키마에 의존하므로, 폴더가 나뉘어 있던 동안 사본이 갈라졌을 가능성이 높다. 통합 Phase 3에서 차이를 항목 단위로 비교해 연구책임자가 원본을 고른다.
- **validator의 위치는 조사 후 정한다.** Claude Code 스킬(`SKILL.md` 보유)이면 `.claude/skills/` 아래에 두어야 자동 인식된다. 일반 도구면 `apps/mapping-validator/`로 간다.
- **`pm/`을 `docs/`와 분리했다.** `docs/`는 제출본 중심의 읽기 전용 기록이고, `pm/`은 매주 바뀌는 현황이다. 규칙도 다르게 걸린다.
- **비밀값과 실데이터는 옮기지 않는다.** IDS 인증서·키, `.env`, KR-GEARs 추출 데이터, 실선 운항 데이터는 통합 대상에서 빼고 `.gitignore`와 `settings.json`의 deny 규칙으로 막았다. 프롬프트 지시는 권고일 뿐이고 실제 차단은 설정이 한다.
- **git 이력은 보존한다.** 원본이 git 저장소면 `git subtree add`로 들여온다.

## 3. 적용 순서

1. k-mds 폴더를 통째로 백업한다(압축 파일 하나면 된다).
2. `k-mds-bootstrap.zip`을 k-mds 루트에 푼다. 기존 파일과 이름이 겹치는 것은 `docs/` 하위 폴더뿐이며, 새 파일만 추가된다. 루트에 이미 `CLAUDE.md`나 `.gitignore`가 있으면 덮어쓰지 말고 내용을 합친다.
3. VS Code에서 k-mds 폴더를 열고 Claude Code를 시작한다. `/context`를 실행해 Memory files에 `CLAUDE.md`와 `AGENTS.md`가 보이는지 확인한다.
4. 아래 프롬프트를 입력한다.

```text
/kmds-consolidate

원본 폴더 경로:
- <imo-compendium-mapping-validator의 절대경로>
- <data-space의 절대경로>
- <kr-ghg-ai-agent의 절대경로>

Phase 0 조사만 하고 INVENTORY.md 요약을 보여 줘. 아무것도 옮기지 마.
```

5. 이후 단계는 승인하면서 진행한다. 세션이 끊겨도 `/kmds-consolidate status`로 이어 간다.

| Phase | 하는 일 | 멈추는 지점 |
| --- | --- | --- |
| 0 | 4개 폴더 조사, 중복 스키마 탐지, 비밀값 파일 위치 목록 (읽기만) | INVENTORY.md 승인 |
| 1 | k-mds 루트의 온톨로지 코드를 `ontology/`로 이동, 테스트 | 이동 계획표 승인, 커밋 후 |
| 2 | validator → data-space → ghg-agent 순으로 들여오기, 폴더마다 테스트 | 폴더마다 |
| 3 | 표준 모델 사본 비교, 원본 확정, `shared/standard-model/`로 단일화 | 원본 선택, 커밋 후 |
| 4 | 하위 CLAUDE.md 정리, 폴더 지도 갱신, 최종 보고 | 종료 |

원본 폴더 3개는 어느 단계에서도 지우지 않는다. 통합본으로 2주 이상 문제없이 작업한 뒤 직접 보관 처리한다.

## 4. 통합 후 사용 예

```text
kmds-pm 서브에이전트로: 성과지표 현황과 제일 급한 것 정리해 줘.
kmds-pm 서브에이전트로: KR 파트 최종평가 예상질의 10개를 3열 표로.
apps/kr-ghg-ai-agent의 Fuel Consumption 매핑을 validator 스킬로 검증하고 갭은 shared/standard-model/gaps.md에 기록해 줘.
```

## 5. 적용 전에 확인할 것

- `pm/kpi/*.csv`의 초기값은 2차 연차보고서(2026-03-20) 기준이다. 3차년도 실적을 반영해 갱신해야 서브에이전트의 답이 현재 상태가 된다. `pm/budget/`에는 RCMS 내보내기 파일을 넣어야 한다. 넣기 전에는 예산 질의에 "집행 자료 없음"으로 답하도록 해 두었다.
- 설계서 v0.2의 도구 6개(`get_kpi_status` 등)는 API 기반 에이전트용 정의다. Claude Code에서는 같은 기능을 파일 읽기로 대체했다(서브에이전트의 "자료 위치와 사용 규칙" 표). 나중에 MCP 서버로 도구를 구현하면 그 표만 바꾸면 된다.
- `settings.json`의 deny 규칙 문법과 서브에이전트·스킬의 frontmatter 필드는 Claude Code 버전에 따라 바뀔 수 있다. 적용 후 `/doctor`와 `/context`로 로드 여부를 확인할 것. 참고: code.claude.com/docs/en/memory, /sub-agents, /skills, /settings
- 이 설계는 4개 폴더의 실제 내용을 보지 않고 설명만으로 만들었다. 언어, 패키지 관리자, git 여부에 따라 Phase 1~2의 세부가 달라지며, 그 판단은 Phase 0 조사 결과를 보고 한다.
