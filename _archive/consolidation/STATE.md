# 통합 진행 상태 (STATE)

| Phase | 상태 | 비고 |
| --- | --- | --- |
| 0 조사 | 완료 2026-09-20 | INVENTORY.md. 승인 대기 결정 5건(§6) |
| 1 루트 정비 | 건너뜀 2026-09-20 | 코드 이미 제자리. verification/ 유지 |
| 2 앱 들여오기 | 완료 2026-09-20 | 복사 방식. validator 71 pass, ghg-agent unit+contract 47 pass, data-space python import OK. 경로 수정: ghg-agent tools/prepare_registry.py DEFAULT_SOURCE, verification/run_c02.py |
| 3 표준 모델 단일화 | 완료 2026-09-20 | data-space `openapi.yaml`→`shared/standard-model/openapi.yaml`, `imo_compendium.md`→`data-model.md`. 구버전 IMO Compendium.xlsx(2026-03) 사본 제거(FAL50이 정본). gaps.md 작성. python/main.py 경로 수정 |
| 4 지침 정리 | 완료 2026-09-20 | apps/*/CLAUDE.md 3개(빌드·테스트·경로), 루트 AGENTS.md 지도 갱신, ghg-agent README 경계표 수정. 루트 quality gate 576 pass |

규칙 변경(사용자 지시 2026-09-20): 단계별 커밋 대신 통합 완료 후 한 번에 커밋. 부트스트랩 커밋 a28799a는 soft reset으로 풀어 작업 트리에 보존.

## 최종 보고 (2026-09-20)

옮긴 것: validator 56파일, kr-ghg-ai-agent 82파일(+var/ 재생성물, git 제외), data-space Ship-ODMS 205파일(워크숍 자료·complete/ 제외).
옮기지 않은 것: `C:\kr-dev\data-space\.env`, `C:\kr-dev\kr-ghg-ai-agent\.env`(IDS·LLM 자격증명), node_modules·.venv·bin/build/obj, data-space 워크숍 README·docs/custom-instructions·images·complete/.
검증: validator 71 pass, ghg-agent unit+contract 47 pass, data-space python import OK(routes 19, shared openapi 해석), k-mds validate(ruff+mypy+pytest 576 pass+schema drift OK).
원본 폴더 3개는 지우지 않았다. 통합본으로 2주 이상 문제없이 쓴 뒤 사용자가 GitHub 저장소를 archive 처리하고 로컬을 보관한다.
