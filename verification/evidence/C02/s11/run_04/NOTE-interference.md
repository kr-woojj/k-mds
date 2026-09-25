# run_04 — 외부 간섭으로 인한 측정 오염 (결과는 수정하지 않음)

- 증상: 이벤트 001·005~011 에서 SKILL_EXECUTION_ERROR(validate_mapping) 10~ 건 → explicit IMO 후보 "확정 차단"(fail-closed) → unmapped 증가, M2 = 0.9394 (< 0.95), R-M2·R-T8 FAIL, 판정 PARTIAL.
- 시각: skill-calls.json 의 실패 호출 17:27:16~17:27:19Z (이벤트 011 기준).
- 원인: 동일 시각(17:26~17:28Z)에 오케스트레이터(세션 S10)가 호스트에서 `uv run pytest`(apps/kr-ghg-ai-agent 단위/통합 테스트)를 실행했고, 테스트와 컨테이너 에이전트가 같은 `var/registry.sqlite3` 를 공유(validator 가 audit event 를 기록) → SQLite 잠금 경합.
- 판단: 시험 대상(에이전트)의 결함이 아니라 시험 환경 운용 오류. fail-closed 정책(허위 매핑 금지)이 설계대로 작동한 것은 확인됨.
- 조치: run_05 를 호스트 무간섭 상태로 재실행. 운용 규칙 추가 — 실행 중 호스트에서 에이전트 테스트/스크립트 금지(README). 권고(미적용, 참조 저장소 수정 승인 필요): validator 의 SQLite 연결에 busy_timeout 설정.
- n8n 실행: http://localhost:5678/workflow/Pycuq2NaVtsIv3xJ/executions/4 (워크플로 자체는 정상 완료).
