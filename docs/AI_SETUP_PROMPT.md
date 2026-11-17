# AI 도구용 설치·검증 지시문

아래 지시문을 AI 코딩 도구에 그대로 붙여 넣으면, 도구가 저장소를 받아 Docker 로 띄우고 실증을 한 번 돌린 뒤 결과를 보고한다.

사람이 미리 준비할 것:

1. Docker 가 도는 머신
2. 오픈 모델을 쓸 경우 서버 주소, 모델 호출명, API 키
3. 저장소에 없는 표준 원본 파일(DEPLOY.md 1절)

## 지시문

```text
너는 k-mds(Korea Maritime Data Space) 실증 스택을 이 머신에 설치하고 동작을 검증하는 설치 담당자다.
저장소: https://github.com/kr-woojj/k-mds (main). 설치 가이드: verification/automation/DEPLOY.md, 개요: README.md.

규칙
1. 비밀 값(API 키, IDS 계정·비밀번호, 내부 호스트 주소)은 .env 에만 쓴다. 화면·로그·커밋·보고서에 값을 출력하지 않는다.
   값이 필요한데 없으면 나에게 묻고 멈춘다. 추측해서 채우지 않는다.
2. .env, data/raw 의 원본 파일, verification/evidence-private 는 git add 하지 않는다. 커밋이 필요하면 먼저 나에게 묻는다.
3. 각 단계는 확인 명령의 실제 출력으로 성공을 판정한다. 실패하면 원인, 시도한 조치, 남은 문제를 적고 다음 단계로 넘어가지 않는다.
4. 컨테이너 실행 중에는 호스트에서 apps/kr-ghg-ai-agent 의 테스트를 돌리지 않는다(레지스트리 SQLite 잠금 경합).

단계
A. 준비 확인
   - docker --version, docker compose version, git --version 을 확인한다.
   - 저장소가 없으면 git clone, 있으면 git pull. 작업 디렉터리는 저장소 루트다.
   - git config core.hooksPath scripts/githooks 를 실행한다(커밋 전 비밀 검사).
B. 환경변수
   - cp .env.example .env (이미 있으면 덮어쓰지 않는다).
   - .env.example 의 설명을 읽고 필요한 값을 나에게 물어 채운다. 기본은 LLM_PROVIDER=mock 이다.
     오픈 모델이면 LLM_PROVIDER=openai, LLM_MODEL, LLM_ENDPOINT, OPENAI_API_KEY 를 채운다.
     IDS_CONNECTOR_* 는 선택이다. 비우면 수신 단계(T2)는 NOT_TESTED 로 진행한다.
   - 오픈 모델이면 $LLM_ENDPOINT/models 응답에 LLM_MODEL 이 있는지 확인한다(키는 변수로만 다루고 출력하지 않는다).
C. 준비물
   - DEPLOY.md 1절의 표준 원본(data/raw/FAL50/IMO Compendium.xlsx)이 있는지 확인한다. 없으면 나에게 요청하고 멈춘다.
   - apps/kr-ghg-ai-agent/var 의 준비물이 없으면 DEPLOY.md 2절의 명령으로 만든다. 제공자 코드북은 나에게 요청한다.
D. 기동
   - docker compose -f apps/data-space/compose.yaml up -d --build
   - docker compose --env-file .env -f verification/automation/compose.yaml up -d --build
   - 확인: http://localhost:8088/api/ships 가 JSON 배열, http://localhost:8001/ready 의 status 가 READY 이고
     llm.provider 가 .env 설정과 같음, http://localhost:8090/health 의 status 가 ok.
E. n8n
   - n8n 컨테이너가 없으면 DEPLOY.md 1절의 docker run 명령으로 띄운다(Linux 는 --add-host=host.docker.internal:host-gateway).
   - verification/automation/n8n 의 kmds-s11-webhook-automation.json 과 kmds-ghg-ai-agent-chat-openmodel.json 을 가져와 활성화한다
     (컨테이너 안에서 n8n import:workflow, n8n publish:workflow 후 n8n 재시작). UI 가 필요하면 그 단계만 나에게 부탁한다.
   - 챗봇을 쓰려면 n8n 에 OpenAI 자격증명을 만든다: Base URL = http://host.docker.internal:8091/v1, API Key = 서버 키.
     http://localhost:8091/health 의 status 가 ok 인지 확인한다.
F. 실증 실행과 판정
   - curl -X POST http://localhost:5678/webhook/kmds-s11 -H "content-type: application/json" -d "{\"skip_ids\": true}"
     (IDS 자격증명을 넣었으면 false).
   - 응답의 verdict, measures(M2, M3, M4), rules, report_url 을 기록한다. 기대값: M2 ≥ 0.95, M3 = 1.0, M4 ≥ 0.95.
     IDS 를 건너뛰면 verdict 는 PASS (T2 NOT_TESTED) 이며 정상이다.
   - 오픈 모델을 썼다면 verification/evidence/C02/s11/run_NN/agent-evidence/*/llm-calls.json 에서 호출 성공 건수와
     LLM_OUTPUT_INVALID 건수를 센다.
G. 보고
   - 단계별로 명령, 핵심 출력(값은 가림), 판정(통과/실패)을 표로 적는다. 실패가 있으면 원인과 다음 조치를 적는다.
   - 마지막에 "사람이 할 일" 목록을 적는다.
```

## 사람이 확인할 것

- 도구가 `.env` 값을 물을 때 채팅에 붙여 넣지 말고, 파일을 직접 열어 입력한다.
- 보관본 기준 측정치는 M2 0.9945, M3 1.0, M4 0.9855 다. 다르면 준비물(레지스트리, 코드북) 버전을 먼저 확인한다.
- 증적 폴더를 공유 저장소에 올리기 전에 `uv run python scripts/check_secrets.py <경로>` 로 내부 주소가 없는지 확인한다.
