# S-1-1 실증 자동화 (n8n + docker)

신규 설치처(RIMS 서울 등) 설치 절차와 오픈 모델 전환은 [DEPLOY.md](DEPLOY.md). n8n 워크플로 내보내기: `n8n/*.json`.

구성: n8n(:5678) 워크플로 `K-MDS S-1-1 실증 자동화` → 하네스(:8090, `harness.py`) + GHG AI Agent(:8001, Gemini) + K-MDS GHG Verifier 포털(Ship-ODMS 기반, API :8088 / UI :3031, 컨테이너 kmds-ghg-verifier-backend·frontend).

```
cp .env.example .env   # 최초 1회, 값 채움 (k-mds/.env 는 커밋되지 않는다)
docker compose --env-file .env -f verification/automation/compose.yaml up -d --build   # 에이전트+하네스
curl -X POST http://localhost:5678/webhook/kmds-s11 -H "content-type: application/json" -d "{\"skip_ids\": false}"
```

- 실행 로그: n8n UI Executions (노드별 입·출력), 결과 보고서: http://localhost:8090/runs/run_NN/report, 증적: `verification/evidence/C02/s11/run_NN/`.
- 단계: T0·T2(하네스) → T3~T5(n8n 이 이벤트별 에이전트 ingress 호출) → T5 증적 수집 → T6 전송 → T7 정합성 → T8 판정(`result.json`, `REPORT.md`).
- LLM 교체: compose 의 `LLM_PROVIDER`/`LLM_MODEL`(+`LLM_ENDPOINT`) 만 변경 (OpenAI 호환 엔드포인트).

운용 규칙: 실행 중에는 호스트에서 에이전트 테스트·스크립트(`uv run pytest` 등)를 돌리지 않는다 — `var/registry.sqlite3` 를 컨테이너와 공유하므로 잠금 경합으로 skill 검증이 실패(fail-closed → unmapped 증가)한다. run_04 NOTE-interference.md 참조.

## AI Agent 대화형 워크플로 (n8n ID toAlr11gvHNYHvvy)
Chat Trigger(공개 채팅 http://localhost:5678/webhook/kmds-ghg-agent-chat/chat, n8n UI 에서 "Open chat") → AI Agent(Gemini 2.5 Flash, 메모리 20턴) → 도구 6개(하네스 `/tools/*`): fetch_ids_data(IDS Consumer 수신, source=ids|snapshot) → map_with_skill(에이전트 ingress 이벤트별 투입) → deliver_to_ship_odms → check_consistency → judge_and_report → get_run_status. 증적·판정은 웹훅 워크플로와 동일한 run_NN 형식(run-meta.orchestrator = n8n-ai-agent). Provider 이벤트 0건이면 에이전트가 사용자에게 보관본(2026-09-12) 사용 여부를 묻는다.

오픈 모델 본(2026-10-08): 같은 워크플로를 복사해 Gemini 노드를 OpenAI Chat Model 노드(RIMS Qwen3.8-27B, 호출명 `qwen`)로 바꾼 `n8n/kmds-ghg-ai-agent-chat-openmodel.json` 을 두었다(채팅 경로 `kmds-chat-qwen-open-model`, 포털 iframe 기본값). Agent 노드는 tool calling 을 쓰는데 RIMS 서버에는 tool-call 파서가 없으므로, 자격증명 Base URL 을 compose 의 `qwen-tool-proxy`(`http://host.docker.internal:8091/v1`, `qwen_tool_proxy.py`)로 둔다. 프록시가 `tool_choice=none` 으로 보내고 본문의 `<tool_call>` 블록을 OpenAI `tool_calls` 로 바꾸며, 사고 과정도 끈다(`/no_think` 프롬프트는 효과 없음). 검증: 도구 호출 7 s, 보관본 전 과정 run_17 PASS(304 s). 웹훅 자동화 워크플로는 tool calling 을 쓰지 않아 서버 직결로 동작한다(run_13·run_16).

단순 채팅 확인본(2026-10-08): 템플릿 `Simple AI Chatbot`(Gemini) 을 복사해 LLM 노드만 RIMS Qwen(`qwen`, 자격증명 `RIMS Qwen (OpenAI 호환)`) 으로 바꾼 `n8n/simple-ai-chatbot-rims-qwen.json`(채팅 경로 `simple-chat-rims-qwen`). 도구가 없어 tool calling 설정과 무관하게 동작하므로 오픈 모델 연결 확인용으로 먼저 쓴다. RIMS 안내서(2026-10-07 메일 첨부 `RIMS_Qwen_API_사용안내_v3`)의 사고 끄기 옵션 `chat_template_kwargs.enable_thinking=false` 는 n8n OpenAI Chat Model 노드가 보내지 못하고 `/no_think` 프롬프트 스위치는 Qwen3.8 에서 무효이므로, 노드 Reasoning Effort=low 로 사고를 줄이고 Agent 뒤 Code 노드가 `</think>` 앞을 잘라낸다. 서버를 `--reasoning-parser qwen3` 로 띄우면 이 후처리는 불필요.

Gemini 할당량: 무료 티어는 모델별 일 20 요청(2026-09-26 확인, gemini-2.5-flash 429 발생). 파이프라인은 run 당 4회, 대화 에이전트는 턴당 수 회 호출하므로 소진 시 다른 모델로 우회한다 — 컨테이너 `LLM_MODEL=gemini-3.5-flash-lite docker compose ... up -d ghg-agent`, n8n 은 "Gemini 2.5 Flash" 노드의 modelName 변경 후 재활성화(publish). gemini-2.5-flash-lite 는 신규 사용자에게 404.

## 추가 서비스 (2026-09-26, `services.py`)
- **선박 조회·연간 GHG 집계**: 도구 `query_ship_data{imo}` → Ship-ODMS 저장 데이터·연차보고 조회(CII 필드는 표준모델에 없음). `compute_annual_ghg{imo, capacity_dwt?, write?}` → 중복 보고 제외 후 연료별 소비(t)·CO2(t)·거리(nm)·GFI TtW(gCO2/MJ) 계산, CF·LCV 는 MEPC.308(73) Annex 5 표(data/raw/MEPC). `write=true` 면 `YearPerformanceReport.totalGfiAnnually` 입력. 증적 `verification/evidence/C02/s11/annual/`. 가정(VLSFO→HFO 행, TtW 만)은 응답 `assumptions` 에 명시.
- **매핑 증적 대시보드**: http://localhost:8090/dashboard?run=run_NN (Chart.js). 총 원본 필드, IMO code 변환 성공/실패, Ship-ODMS 전달 대조 성공/불일치, 대상 필드 없음, 코드북(랩오투원) 변환/미해결 항목, 이벤트별 표, M2/M3/M4. 도구 `mapping_dashboard{run_id?}` 가 같은 수치를 돌려준다. 원시 JSON: `/dashboard/data?run=`.

포털(K-MDS GHG Verifier, apps/data-space compose): 메뉴 순서 챗봇(/chat, n8n hosted chat iframe) → 선박 목록(/) → 대시보드(/dashboard, 하네스 /dashboard iframe). iframe 주소는 compose 의 Portal__ChatUrl / Portal__DashboardUrl 로 바꾼다. 컨테이너·네트워크 이름 2026-09-26 변경(ship-odms-* → kmds-ghg-verifier-*), 하네스 compose 의 SHIP_ODMS_BASE·external network 도 함께 변경됨.
