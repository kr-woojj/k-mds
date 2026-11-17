# 실증 자동화 (n8n + docker)

설치 절차는 [DEPLOY.md](DEPLOY.md)에 있다. 여기서는 구성과 동작을 설명한다.

## 구성

| 구성요소 | 주소 | 역할 |
| --- | --- | --- |
| n8n 워크플로 (`n8n/*.json`) | :5678 | 웹훅 자동화와 대화형 AI Agent |
| 하네스 (`harness.py`, `services.py`) | :8090 | 단계 실행, 증적, 판정, 대시보드, 챗봇 도구 |
| GHG AI Agent | :8001 | 매핑·검증(시험 대상) |
| tool-call 프록시 (`tool_call_proxy.py`) | :8091 | tool calling 을 지원하지 않는 모델 서버용 변환 |
| K-MDS GHG Verifier (`apps/data-space`) | :8088 / :3031 | 표준모델 API 와 포털 |

## 실행

```bash
docker compose --env-file .env -f verification/automation/compose.yaml up -d --build
curl -X POST http://localhost:5678/webhook/kmds-s11 -H "content-type: application/json" -d "{\"skip_ids\": false}"
```

단계: T0 기준선 → T2 IDS 수신 → T3~T5 에이전트 매핑·검증 → T6 표준모델 전달 → T7 정합성 대조 → T8 판정.

| 결과 | 위치 |
| --- | --- |
| 증적 | `verification/evidence/C02/s11/run_NN/` (`result.json`, `REPORT.md`, 대조 CSV 포함) |
| 판정 보고서 | `http://localhost:8090/runs/run_NN/report` |
| 대시보드 | `http://localhost:8090/dashboard?run=run_NN` (원시 JSON: `/dashboard/data?run=`) |
| 정합성 대조 | `GET /runs/run_NN/consistency`, `/consistency.csv` (포털의 정합성 대조 화면이 읽는다) |
| 실행 로그 | n8n UI 의 Executions |

호스트에서 n8n 없이 돌리려면 `verification/run_s11.py --run` 을 쓴다. 실선 데이터는 `S11_EVIDENCE_DIR` 로 `verification/evidence-private/` 아래를 지정한다.

## 대화형 AI Agent

채팅 주소는 `http://localhost:5678/webhook/kmds-chat-open-model/chat` 이고 포털의 챗봇 메뉴가 이 주소를 연다.
에이전트는 하네스의 도구(`/tools/*`)를 호출한다.

| 도구 | 하는 일 |
| --- | --- |
| `fetch_ids_data` | IDS Consumer 로 데이터를 받아 새 run 을 연다(`source`: ids 또는 snapshot) |
| `map_with_skill` | 이벤트별로 에이전트에 넣어 매핑·검증한다 |
| `deliver_to_ship_odms` | 표준모델 API 로 전달한다 |
| `check_consistency`, `judge_and_report`, `get_run_status` | 정합성 대조, 판정, 상태 조회 |
| `query_ship_data` | IMO 번호로 저장 데이터와 연차보고를 조회한다 |
| `compute_annual_ghg` | 연도별 연료 소비·CO2·거리·GFI 를 계산한다. `write=true` 면 연차보고에 저장한다 |
| `mapping_dashboard` | 대시보드와 같은 수치를 돌려준다 |

- Provider 이벤트가 0건이면 에이전트가 보관본 사용 여부를 묻는다.
- 연간 집계의 CF·LCV 는 MEPC.308(73) 표를 쓰고, 가정은 응답의 `assumptions` 에 적힌다. 연도를 주지 않으면 가장 최근 연도로 계산한다.
- 연간 집계 증적은 시험 선박이면 `evidence/C02/s11/annual/`, 그 외 선박이면 `evidence-private/annual/` 에 쓴다.
- 모델 서버가 tool calling 을 지원하지 않으면 n8n 자격증명의 Base URL 을 프록시(`http://host.docker.internal:8091/v1`)로 둔다. 웹훅 자동화는 tool calling 을 쓰지 않는다.

## 운용 규칙

컨테이너 실행 중에는 호스트에서 에이전트 테스트를 돌리지 않는다. `var/registry.sqlite3` 를 컨테이너와 함께 쓰므로 잠금 경합이 나면 검증이 실패하고 미매핑이 늘어난다.
