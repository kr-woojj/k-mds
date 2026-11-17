# 실증 스택 설치 가이드

저장소를 받아 환경변수와 n8n 가져오기만으로 실증 자동화·포털·챗봇을 띄우는 절차다. 소스 수정은 없다.

## 1. 준비물

| 항목 | 내용 |
| --- | --- |
| 런타임 | Windows 11 또는 Linux, Docker(compose v2). 이미지 빌드에 인터넷이 필요하다 |
| 저장소 | `git clone https://github.com/kr-woojj/k-mds.git` |
| 표준 원본 (저장소에 없음) | `data/raw/FAL50/IMO Compendium.xlsx`(필수), `data/raw/ISO25000/`, `data/raw/MEPC/`(보고서·연간 집계용). 한국선급이 따로 전달한다 |
| 에이전트 준비물 (저장소에 없음) | `apps/kr-ghg-ai-agent/var/` 의 `registry.sqlite3`, `candidate-inventory.json`, `reference/code_lists.json`, `reference/lab021/noon-code-book.json`. 2절에서 만들거나 전달본을 복사한다 |
| 오픈 모델 서버 (선택) | OpenAI 호환 API 와 구조화 출력(`response_format: json_schema`). tool calling 은 챗봇에만 필요하고, 서버가 지원하지 않으면 tool-call 프록시(:8091)가 대신한다 |
| n8n | 1.119 이상(2.23 에서 검증). `docker run -d --name n8n -p 5678:5678 -v <dir>:/home/node/.n8n n8nio/n8n` |
| 포트 | 8088(표준모델 API), 3031(포털), 8001(에이전트), 8090(하네스), 8091(프록시), 5678(n8n) |

## 2. 에이전트 준비물 생성

전달본이 없을 때만 실행한다.

```bash
cd apps/kr-ghg-ai-agent
uv sync
uv run python tools/prepare_registry.py            # registry.sqlite3, reference/code_lists.json
uv run python tools/build_candidate_inventory.py   # candidate-inventory.json
```

제공자 코드북(`reference/lab021/noon-code-book.json`)은 한국선급 전달본을 쓴다.

## 3. 환경변수

```bash
cp .env.example .env
```

변수 설명은 `.env.example` 에 있다. 기본은 `LLM_PROVIDER=mock` 이며, 오픈 모델을 쓰려면 `LLM_PROVIDER=openai` 와 `LLM_MODEL`, `LLM_ENDPOINT`, `OPENAI_API_KEY` 를 채운다.
IDS 커넥터 항목을 비우면 수신 단계(T2)는 NOT_TESTED 로 기록되고 보관본으로 진행한다.

## 4. 기동

```bash
docker compose -f apps/data-space/compose.yaml up -d --build
docker compose --env-file .env -f verification/automation/compose.yaml up -d --build
curl http://localhost:8088/api/ships      # []
curl http://localhost:8001/ready          # "status":"READY", llm.provider 가 .env 설정과 같다
curl http://localhost:8090/health         # "status":"ok"
```

포털이 여는 챗봇·대시보드 주소를 바꾸려면 `apps/data-space/compose.yaml` 의 `Portal__ChatUrl`, `Portal__DashboardUrl` 을 고친다.

## 5. n8n 워크플로

1. n8n → Workflows → Import from File 로 `verification/automation/n8n/` 의 두 파일을 가져온다.
   - `kmds-s11-webhook-automation.json`: 웹훅 자동화
   - `kmds-ghg-ai-agent-chat-openmodel.json`: 대화형 AI Agent(챗봇)
2. 챗봇용 OpenAI 자격증명을 만들어 모델 노드에 지정한다.
   - Base URL: `http://host.docker.internal:8091/v1` (tool-call 프록시). 서버가 tool calling 을 지원하면 서버 주소를 직접 써도 된다
   - API Key: 서버가 발급한 키(검사가 없으면 임의 문자열)
   - 모델 노드의 `model` 값을 서버의 모델 호출명으로 맞춘다
3. 두 워크플로를 활성화(Publish)한다. 웹훅 경로는 `kmds-s11`, 채팅 경로는 `kmds-chat-open-model` 이다.
4. n8n 은 하네스와 에이전트를 `http://host.docker.internal:8090`, `:8001` 로 부른다. Linux 에서 이 이름이 없으면 n8n 컨테이너에 `--add-host=host.docker.internal:host-gateway` 를 준다.

## 6. 동작 확인

```bash
curl -X POST http://localhost:5678/webhook/kmds-s11 -H "content-type: application/json" -d "{\"skip_ids\": true}"
```

- 기대 결과(보관본 12 이벤트): `verdict` 가 `PASS (T2 NOT_TESTED …)`, M2 0.9945 / M3 1.0 / M4 0.9855. 측정치는 결정론 매핑이 정하므로 모델이 달라도 같아야 한다.
- 화면: 포털 <http://localhost:3031>, 판정 보고서 `http://localhost:8090/runs/run_NN/report`, 대시보드 <http://localhost:8090/dashboard>.
- 챗봇: 포털의 챗봇 메뉴에서 "보관본으로 IDS 데이터를 매핑해서 GHG Verifier 에 입력하고 판정까지 보고해줘".
- 오픈 모델 확인: 증적 `agent-evidence/<cid>/llm-calls.json` 의 provider 가 `openai` 이면 된다. `LLM_OUTPUT_INVALID` 가 있으면 모델이 구조화 출력을 지키지 못한 것이며, 해당 필드는 미매핑으로 남는다.

## 7. 운용 규칙

- 컨테이너 실행 중에는 호스트에서 `apps/kr-ghg-ai-agent` 의 테스트를 돌리지 않는다(registry SQLite 잠금 경합).
- 증적 `verification/evidence/C02/s11/run_NN/` 은 덮어쓰지 않는다. 실선 데이터와 참여기관 인프라 주소가 든 증적은 저장소에 올리지 않는다.
- 비밀 값은 `.env` 에만 두고 로그·증적·커밋에 남기지 않는다.
- 데이터 초기화: `DELETE http://localhost:8088/api/ships/{id}` (하위 데이터까지 삭제). 실행 전에 `apps/data-space/java/ship_odms/ship_odms.db` 를 백업한다.
