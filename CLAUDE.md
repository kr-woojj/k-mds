@AGENTS.md

## Claude Code 전용

- 사업관리 질의(성과지표, 예산, 최종평가, 참여기관 조율)는 `kmds-pm` 서브에이전트에 위임한다.
- 폴더 통합·정리는 `/kmds-consolidate` 스킬로만 수행한다. 스킬 밖에서 폴더를 옮기거나 지우지 않는다.
- 매핑 검증은 `apps/imo-compendium-mapping-validator/`(FastAPI 앱)를 실행해서 한다. 매핑 표를 눈으로만 검토하고 "통과"라고 하지 않는다.
- 두 개 이상의 앱에 걸친 변경은 plan mode로 계획을 먼저 보여 준다.
- 세부 규칙은 `.claude/rules/`에 경로별로 있다. 해당 폴더의 파일을 읽을 때 자동으로 붙는다.
