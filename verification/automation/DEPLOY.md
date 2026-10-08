# K-MDS S-1-1 실증 스택 설치 가이드 (RIMS 서울 사무소 등 신규 설치처용)

목표: 저장소를 받아 **LLM 설정(오픈 모델 엔드포인트)만 바꾸면** 실증 자동화·포털·챗봇이 그대로 동작하게 한다. 소스 수정 없이 환경변수와 n8n 가져오기만으로 끝난다.

## 1. 준비물
| 항목 | 요구 |
|---|---|
| OS / 런타임 | Windows 11 또는 Linux, Docker Desktop(또는 docker + compose v2). 이미지 빌드 시 인터넷 필요(pip/uv/NuGet/Maven). |
| 저장소 | `git clone https://github.com/kr-woojj/k-mds.git` (main). |
| 표준 원본 (git 미포함, 라이선스) | `data/raw/FAL50/IMO Compendium.xlsx`, `data/raw/ISO25000/ISO_IEC_DIS_25023(E)-Character_PDF_document.pdf`, `data/raw/MEPC/MEPC.308(73).pdf` — 한국선급이 별도 전달. FAL50 은 필수(registry 생성), 나머지는 보고서·부가 서비스용. |
| 에이전트 준비물 (git 미포함) | `apps/kr-ghg-ai-agent/var/registry.sqlite3`, `var/candidate-inventory.json`, `var/reference/code_lists.json`, `var/reference/lab021/noon-code-book.json` — 아래 2단계에서 생성하거나 한국선급 전달본을 복사. |
| 오픈 모델 서버 | OpenAI 호환 API(`/v1/chat/completions`, tool/function calling 및 JSON 구조화 출력 지원 필요). vLLM·Ollama·LM Studio 등. |
| n8n | 1.119 이상 권장(2.23 에서 검증). `docker run -d --name n8n -p 5678:5678 -v <dir>:/home/node/.n8n n8nio/n8n`. |
| 포트 | 8088(표준모델 API), 3031(포털), 8001(에이전트), 8090(하네스), 5678(n8n). |

## 2. 에이전트 준비물 생성 (전달본이 없을 때)
```bash
cd apps/kr-ghg-ai-agent
uv sync
uv run python tools/prepare_registry.py            # data/raw/FAL50 → var/registry.sqlite3, var/reference/code_lists.json
uv run python tools/build_candidate_inventory.py   # var/candidate-inventory.json (0.2.0-provisional, 159 요소)
# var/reference/lab021/noon-code-book.json 은 vessellink 코드북(공개 GET) — 한국선급 전달본 사용 또는 README 의 URL 로 재수집
```

## 3. 환경변수 파일
저장소 루트의 `k-mds/.env` 에 값을 둔다. 이 파일은 `.gitignore` 에 등록되어 커밋되지 않는다.
템플릿 `k-mds/.env.example` 을 복사해 만들며, 각 항목의 `<sample: …>` 설명을 보고 값을 채운다.
```bash
cd k-mds && cp .env.example .env
```
오픈 모델로 쓸 때 바뀌는 항목:
```
# 오픈 모델
LLM_PROVIDER=openai
LLM_MODEL=<서버에 올린 모델명>
LLM_ENDPOINT=http://<open-model-host>:<port>/v1
OPENAI_API_KEY=local
# (선택) K-MDS IDS Consumer — 없으면 T2 는 NOT_TESTED 로 기록되고 보관본으로 진행
IDS_CONNECTOR_BASE=
IDS_CONNECTOR_USER=
IDS_CONNECTOR_PASSWORD=
```

## 4. 기동
```bash
cd k-mds
docker compose -f apps/data-space/compose.yaml up -d --build                         # 표준모델 API :8088 + 포털 :3031
docker compose --env-file .env -f verification/automation/compose.yaml up -d --build   # 에이전트 :8001 + 하네스 :8090
curl http://localhost:8088/api/ships      # []
curl http://localhost:8001/ready          # "status":"READY", llm.provider "openai", real true
curl http://localhost:8090/health         # "status":"ok"
```
포털 챗봇·대시보드 iframe 주소(브라우저 기준)를 다른 호스트로 바꾸려면 `apps/data-space/compose.yaml` 의 `Portal__ChatUrl`, `Portal__DashboardUrl` 를 수정한다.

## 5. n8n 워크플로 가져오기
1. n8n → Workflows → Import from File: `verification/automation/n8n/kmds-s11-webhook-automation.json`, `kmds-ghg-ai-agent-chat.json`.
2. 자격증명: 챗봇 워크플로의 모델 노드는 Gemini 로 저장돼 있다. 오픈 모델은 **OpenAI Chat Model 노드로 교체** → OpenAI 자격증명에 Base URL = `http://<open-model-host>:<port>/v1`, API Key = 임의 문자열, 모델명 지정. (n8n 에서 워크플로 노드 교체는 UI 로 1분.)
3. 두 워크플로를 **활성화(Publish)**. 웹훅 경로 `kmds-s11`, 채팅 경로 `kmds-ghg-agent-chat` 는 그대로 둔다(포털 iframe 이 이 경로를 쓴다).
4. n8n 이 호스트의 하네스·에이전트에 접속하는 주소는 `http://host.docker.internal:8090`, `:8001` 이다. Linux 에서 `host.docker.internal` 이 없으면 n8n 컨테이너에 `--add-host=host.docker.internal:host-gateway` 를 준다.

## 6. 동작 확인
```bash
curl -X POST http://localhost:5678/webhook/kmds-s11 -H "content-type: application/json" -d "{\"skip_ids\": true}"
# → verdict "PASS (T2 NOT_TESTED …)", measures M2 0.9945 / M3 1.0 / M4 0.9854 (2026-09-12 보관본 12 이벤트 기준)
```
- 보고서 `http://localhost:8090/runs/run_01/report`, 대시보드 `http://localhost:8090/dashboard`, 포털 `http://localhost:3031`.
- 챗봇: 포털 "챗봇" 메뉴에서 "보관본으로 IDS 데이터를 매핑해서 Ship-ODMS 에 입력하고 판정까지 보고해줘".
- 오픈 모델 확인: run 증적 `agent-evidence/<cid>/llm-calls.json` 의 provider 가 `openai`, model 이 지정한 모델명이면 된다. 구조화 출력(JSON schema)을 지원하지 않는 모델이면 `LLM_OUTPUT_INVALID` 경고가 남고 해당 필드는 UNMAPPED 로 유지된다(허위 매핑 차단). 측정치 M2·M3·M4 는 결정적 매핑이 지배하므로 모델과 무관하게 같아야 한다.

## 7. 운용 규칙
- 실행 중 호스트에서 `apps/kr-ghg-ai-agent` 테스트·스크립트를 돌리지 않는다(registry SQLite 잠금 경합).
- 증적 `verification/evidence/C02/s11/run_NN/` 은 덮어쓰지 않는다. 참여기관 인프라 주소가 든 증적은 저장소에 올리지 않는다.
- 비밀 값(API 키, IDS 자격증명)은 env 파일에만 두고 로그·증적·커밋에 남기지 않는다.
- 데이터 초기화: `DELETE http://localhost:8088/api/ships/{id}` (하위 데이터 연쇄 삭제). 실행 전 `apps/data-space/java/ship_odms/ship_odms.db` 백업.
