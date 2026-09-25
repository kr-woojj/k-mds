# S-1-1 실증 자동화 (n8n + docker)

구성: n8n(:5678) 워크플로 `K-MDS S-1-1 실증 자동화` → 하네스(:8090, `harness.py`) + GHG AI Agent(:8001, Gemini) + Ship-ODMS(:8088/UI :3030).

```
docker compose --env-file C:/kr-dev/.env.master -f verification/automation/compose.yaml up -d --build   # 에이전트+하네스
curl -X POST http://localhost:5678/webhook/kmds-s11 -H "content-type: application/json" -d "{\"skip_ids\": false}"
```

- 실행 로그: n8n UI Executions (노드별 입·출력), 결과 보고서: http://localhost:8090/runs/run_NN/report, 증적: `verification/evidence/C02/s11/run_NN/`.
- 단계: T0·T2(하네스) → T3~T5(n8n 이 이벤트별 에이전트 ingress 호출) → T5 증적 수집 → T6 전송 → T7 정합성 → T8 판정(`result.json`, `REPORT.md`).
- LLM 교체: compose 의 `LLM_PROVIDER`/`LLM_MODEL`(+`LLM_ENDPOINT`) 만 변경 (OpenAI 호환 엔드포인트).

운용 규칙: 실행 중에는 호스트에서 에이전트 테스트·스크립트(`uv run pytest` 등)를 돌리지 않는다 — `var/registry.sqlite3` 를 컨테이너와 공유하므로 잠금 경합으로 skill 검증이 실패(fail-closed → unmapped 증가)한다. run_04 NOTE-interference.md 참조.
