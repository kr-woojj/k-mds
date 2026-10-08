# AI 도구용 설치·검증 지시문

아래 지시문을 Claude Code, Codex, GitHub Copilot 에이전트 등에 **그대로 붙여 넣는다.** 도구는 저장소를 받아 Docker 로 띄우고 실증을 한 번 돌린 뒤 결과를 보고한다.
사람이 미리 준비할 것은 세 가지다: (1) Docker 가 도는 머신, (2) 오픈 모델 서버의 주소·모델명·API 키 또는 Gemini 키, (3) 표준 원본 파일(FAL 등, 저장소에 없음 — DEPLOY.md §1).

---

```text
너는 k-mds(Korea Maritime Data Space) 실증 스택을 이 머신에 설치하고 동작을 검증하는 설치 담당자다.
저장소: https://github.com/kr-woojj/k-mds (main). 설치 가이드: verification/automation/DEPLOY.md, 개요: README.md.

규칙
1. 비밀 값(API 키, IDS 계정·비밀번호, 내부 호스트 주소)은 .env 에만 쓴다. 화면·로그·커밋·보고서에 값을 출력하지 않는다. 값이 필요한데 없으면 나에게 묻고 멈춘다. 추측해서 채우지 않는다.
2. .env, data/raw 의 원본 파일, verification/evidence-private 는 절대 git add 하지 않는다. 커밋이 필요하면 먼저 나에게 묻는다.
3. 각 단계는 확인 명령의 실제 출력으로 성공을 판정한다. 출력을 보지 않고 성공이라고 쓰지 않는다. 실패하면 원인·시도한 조치·남은 문제를 적고 다음 단계로 넘어가지 않는다.
4. 실행 중에는 호스트에서 apps/kr-ghg-ai-agent 의 pytest·스크립트를 돌리지 않는다(레지스트리 SQLite 잠금 경합).

단계
A. 준비 확인
   - docker --version, docker compose version, git --version 을 확인한다.
   - 저장소가 없으면 git clone, 있으면 git pull. 작업 디렉터리를 저장소 루트로 한다.
   - git config core.hooksPath scripts/githooks 를 실행한다(커밋 전 비밀 검사).
B. 환경변수
   - cp .env.example .env (이미 있으면 덮어쓰지 않는다).
   - .env.example 의 <sample: …> 설명을 읽고 다음을 나에게 물어 .env 에 채운다: LLM 구성(오픈 모델이면 LLM_PROVIDER=openai, LLM_MODEL, LLM_ENDPOINT, OPENAI_API_KEY, LLM_DISABLE_THINKING=true, LLM_REASONING_EFFORT=low / Gemini 면 LLM_PROVIDER=gemini, GEMINI_API_KEY), 선택 항목 IDS_CONNECTOR_BASE/USER/PASSWORD(없으면 비워 두고 T2 는 NOT_TESTED 로 진행).
   - 오픈 모델이면 연결을 확인한다: curl -s $LLM_ENDPOINT/models -H "Authorization: Bearer $OPENAI_API_KEY" 의 응답에 LLM_MODEL 이 있어야 한다(키 값은 변수로만 다루고 출력하지 않는다).
C. 준비물
   - DEPLOY.md §1 의 표준 원본(data/raw/FAL50/IMO Compendium.xlsx 등)이 있는지 확인한다. 없으면 나에게 요청하고 멈춘다.
   - apps/kr-ghg-ai-agent/var/registry.sqlite3, var/candidate-inventory.json, var/reference/code_lists.json, var/reference/lab021/noon-code-book.json 이 없으면 DEPLOY.md §2 의 명령으로 생성한다. 코드북은 전달본이 필요하면 나에게 요청한다.
D. 기동
   - docker compose -f apps/data-space/compose.yaml up -d --build
   - docker compose --env-file .env -f verification/automation/compose.yaml up -d --build
   - 확인: curl http://localhost:8088/api/ships 가 JSON 배열, curl http://localhost:8001/ready 의 status 가 READY 이고 llm.provider 가 .env 의 설정이며 llm.real 이 true, curl http://localhost:8090/health 의 status 가 ok.
E. n8n
   - n8n 컨테이너가 없으면 DEPLOY.md §1 의 docker run 명령으로 띄운다(Linux 는 --add-host=host.docker.internal:host-gateway 추가).
   - verification/automation/n8n/kmds-s11-webhook-automation.json 을 가져와 활성화한다. UI 가 필요하면 나에게 그 단계만 부탁한다(컨테이너 안 n8n CLI 의 import:workflow 와 update:workflow --active=true 로도 된다).
   - 대화형 AI Agent 워크플로(kmds-ghg-ai-agent-chat*.json)는 오픈 모델 서버가 tool calling 을 지원할 때만 가져온다(README 「LLM 선택」). 지원 여부는 /v1/chat/completions 에 tools 를 넣어 보내 400 이 아닌지로 확인한다.
F. 실증 실행과 판정
   - curl -X POST http://localhost:5678/webhook/kmds-s11 -H "content-type: application/json" -d "{\"skip_ids\": true}" (IDS 자격증명을 넣었으면 false).
   - 응답 JSON 의 verdict, measures(M2, M3, M4), rules, report_url 을 기록한다. 기대값: M2 ≥ 0.95, M3 = 1.0, M4 ≥ 0.95. IDS 를 건너뛰면 verdict 는 PASS(T2 NOT_TESTED) 또는 PARTIAL(R-T2 만 false)이며 이는 정상이다.
   - verification/evidence/C02/s11/run_NN/agent-evidence/*/llm-calls.json 에서 provider·model 이 .env 설정과 같고 ok 가 모두 true 인지 센다. LLM_OUTPUT_INVALID 가 있으면 건수를 적는다.
G. 보고
   - 단계별 결과를 표로 적는다: 명령, 핵심 출력(값 마스킹), 판정(통과/실패). 실패가 있으면 원인과 다음 조치를 적는다.
   - 마지막에 "사람이 할 일" 목록을 적는다(예: UI 에서 워크플로 활성화, 자격증명 발급 요청).
```

---

## 사람이 확인할 것

- 도구가 `.env` 를 만들 때 값을 묻는다. 채팅에 값을 붙여 넣는 대신, 도구가 파일을 열어 두면 직접 입력하는 쪽이 안전하다.
- 보고서의 측정치가 README 「LLM 선택」의 검증 결과(M2 0.9945, M3 1.0, M4 0.9854)와 같은 보관본 기준에서 다르면 준비물(레지스트리·코드북) 버전을 먼저 의심한다.
- 증적 폴더 `verification/evidence/C02/s11/run_NN` 은 설치처의 기록이다. 공유 저장소에 올리기 전에 `uv run python scripts/check_secrets.py <경로>` 로 내부 주소가 없는지 확인한다.
