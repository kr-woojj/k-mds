# k-mds

Korea Maritime Data Space — IMO Compendium on Facilitation and Electronic Business 참조모델 기반 해사 데이터 상호운용 플랫폼.

선박이 보내는 운항·연료·배출 보고 데이터를 **IMO Compendium 데이터 번호로 매핑·검증**하고, 표준모델 데이터베이스(Ship-ODMS)에 적재한 뒤 **정합성(ISO/IEC 25023 기준 측정치)을 자동 판정**한다.
LLM 은 후보 제안에만 쓰이고 최종 판정은 결정론 검증기가 한다. 상용 모델(Gemini 등)과 **오픈 모델(OpenAI 호환 서버, vLLM 의 Qwen3 등)** 을 환경변수만으로 바꿔 쓸 수 있다.

## 구성

| 구성요소 | 경로 | 역할 | 포트 |
| --- | --- | --- | --- |
| GHG AI Agent | `apps/kr-ghg-ai-agent` | 수신 데이터 → IMO Compendium 매핑 후보(LLM) → 스킬 검증 → 표준모델 입력 | 8001 |
| IMO Compendium 매핑 검증기 | `apps/imo-compendium-mapping-validator` | 참조모델(FAL 버전) 레지스트리와 결정론 검증 스킬 | (라이브러리) |
| K-MDS GHG Verifier | `apps/data-space` | Ship-ODMS 표준모델 API 와 포털(선박 목록·챗봇·대시보드) | 8088 / 3031 |
| S-1-1 실증 하네스 | `verification/automation` | T0~T8 단계 실행, 측정치 M2·M3·M4, 판정 보고서·증적 | 8090 |
| n8n 워크플로 | `verification/automation/n8n` | 웹훅 자동화, 대화형 AI Agent (내보내기 JSON) | 5678 |

흐름: 데이터 제공자(IDS Provider) → K-MDS IDS Consumer → GHG AI Agent(매핑·검증) → Ship-ODMS(표준모델) → 정합성 판정·보고서.

## 빠른 시작 (Docker)

요구사항: Docker(compose v2), git. 이미지 빌드에 인터넷이 필요하다. 호스트에서 개발·검증까지 하려면 Python 3.11 과 [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/kr-woojj/k-mds.git && cd k-mds
cp .env.example .env            # <sample: …> 설명을 보고 값을 채운다 (커밋되지 않는다)
```

1. **표준 원본과 에이전트 준비물**을 둔다. 라이선스 때문에 저장소에 없는 파일(FAL 원본 xlsx 등)과 생성 절차는 [verification/automation/DEPLOY.md](verification/automation/DEPLOY.md) §1~§2.
2. **기동**

   ```bash
   docker compose -f apps/data-space/compose.yaml up -d --build                           # 표준모델 API :8088, 포털 :3031
   docker compose --env-file .env -f verification/automation/compose.yaml up -d --build   # 에이전트 :8001, 하네스 :8090
   curl http://localhost:8001/ready     # "status":"READY", llm.provider 가 .env 의 설정, real true
   curl http://localhost:8090/health    # "status":"ok"
   ```

3. **n8n** 을 띄우고(`docker run -d --name n8n -p 5678:5678 -v <dir>:/home/node/.n8n n8nio/n8n`) `verification/automation/n8n/*.json` 을 가져온 뒤 활성화한다. 절차는 DEPLOY.md §5.
4. **실증 실행**

   ```bash
   curl -X POST http://localhost:5678/webhook/kmds-s11 -H "content-type: application/json" -d "{\"skip_ids\": true}"
   ```

   응답의 `verdict`, `measures`(M2 매핑 완결성, M3 검증 정확성, M4 정합율)와 `report_url` 을 본다. 증적은 `verification/evidence/C02/s11/run_NN/`.

## LLM 선택

`.env` 의 `LLM_PROVIDER` 로 고른다. 코드 수정은 없다.

| 구성 | 환경변수 | 비고 |
| --- | --- | --- |
| Gemini | `LLM_PROVIDER=gemini`, `GEMINI_API_KEY` | 무료 티어는 모델별 일 요청 한도가 있어 실증에는 부족할 수 있다 |
| 오픈 모델 (OpenAI 호환) | `LLM_PROVIDER=openai`, `LLM_MODEL`, `LLM_ENDPOINT=http://<host>:<port>/v1`, `OPENAI_API_KEY` | vLLM · Ollama · LM Studio. **검증된 구성: vLLM 의 Qwen3.8-27B(호출명 `qwen`)**, `LLM_DISABLE_THINKING=true`, `LLM_REASONING_EFFORT=low` |
| OpenAI / Azure OpenAI | `OPENAI_API_KEY` 또는 `AZURE_OPENAI_*` | 선택 |

오픈 모델 서버가 갖춰야 하는 것:

- `/v1/chat/completions` 와 `response_format: json_schema`(구조화 출력). 파이프라인(에이전트·하네스·웹훅 워크플로)은 이것만 쓴다.
- **tool calling** 은 **대화형 AI Agent 워크플로(n8n Agent 노드)** 에만 필요하다. vLLM 은 `--enable-auto-tool-choice --tool-call-parser hermes`(Qwen3) 로 띄워야 한다. 이 플래그 없이 Agent 노드를 쓰면 서버가 `400 "auto" tool choice requires --enable-auto-tool-choice` 를 돌려준다.

2026-10-08 검증 결과(RIMS 테스트 서버 Qwen3.8-27B): 파이프라인 전 단계 통과, LLM 호출 4/4 성공, 호출당 중앙값 4.8초, 측정치 M2 0.9945 · M3 1.0 · M4 0.9854 로 Gemini 실행과 동일.

## 운영 수칙

- 실행 중에는 호스트에서 `apps/kr-ghg-ai-agent` 의 테스트·스크립트를 돌리지 않는다. 컨테이너와 레지스트리 SQLite 를 공유하므로 잠금 경합으로 검증이 실패한다.
- 증적 폴더 `run_NN` 은 덮어쓰지 않는다. 참여기관 인프라 주소가 든 증적은 저장소에 올리지 않는다.
- 데이터 초기화와 백업은 DEPLOY.md §7.

## AI 도구로 자동 설치·검증

Claude Code, Codex, Copilot 같은 AI 코딩 도구에 [docs/AI_SETUP_PROMPT.md](docs/AI_SETUP_PROMPT.md) 의 지시문을 그대로 주면 포크·클론부터 Docker 기동, 실증 실행, 결과 판정까지 수행하고 보고한다. 지시문은 비밀 값을 출력하거나 커밋하지 않도록 제한되어 있다.

## 개발

요구사항: Python 3.11 (`.python-version`), [uv](https://docs.astral.sh/uv/), GNU Make(선택).
모든 검증 명령은 Cross-platform 단일 진입점 `scripts/dev.py`를 사용한다. Makefile, VSCode Task, CI가 동일한 dev.py 로직을 호출한다.

```bash
uv sync                                  # 의존성 설치 (= make setup)
uv run python scripts/dev.py build      # Compile + Import 검증 (= make build)
uv run python scripts/dev.py validate   # Ruff + MyPy + Pytest Quality Gate (= make validate)
uv run python scripts/dev.py test       # Pytest (= make test)
```

개발 규약은 Root [AGENTS.md](AGENTS.md)를 Master Contract로 따른다. 경계 폴더(`data/`, `ontology/`, `schemas/`, `src/`, `tests/`)에는 추가 제약을 담은 Local AGENTS.md가 있다.

### 환경변수와 비밀정보

실제 값(LLM API 키, K-MDS IDS 커넥터 계정 등)은 저장소 루트의 `.env` 한 곳에 둔다. 이 파일은 `.gitignore` 에 등록되어 커밋되지 않는다.
포크·클론한 기관은 템플릿 `.env.example` 의 `<sample: …>` 설명을 보고 `.env` 를 만든다.

```bash
cp .env.example .env                                   # 값을 채운다
git config core.hooksPath scripts/githooks             # 커밋 전 비밀정보 검사 훅 (클론마다 한 번)
uv run python scripts/check_secrets.py --staged        # 수동 검사. CI 는 --all 로 추적 파일 전체를 검사한다
```

`.env` 를 읽는 곳: docker compose(`--env-file .env`), `verification/run_s11.py`, 에이전트 라이브 LLM 시험. 로그·증적·커밋 메시지에 값을 적지 않는다.

## 문제 해결

| 증상 | 원인·조치 |
| --- | --- |
| `/ready` 의 `llm.real` 이 false | `ALLOW_LIVE_LLM`·키가 컨테이너에 안 들어감. `docker compose --env-file .env … up -d ghg-agent` 로 다시 띄운다 |
| 증적 `llm-calls.json` 에 `LLM_OUTPUT_INVALID` | 모델이 JSON 구조화 출력을 못 지킴. 해당 필드는 UNMAPPED 로 남는다(허위 매핑 차단). 모델을 바꾸거나 `LLM_DISABLE_THINKING=true` 로 둔다 |
| 챗봇이 `Error in workflow` | 오픈 모델 서버에 tool calling 파서가 없다. 위 「LLM 선택」의 vLLM 플래그 |
| `verdict` 가 PARTIAL 이고 `R-T2 IDS 전달` 만 false | IDS Provider 에 데이터가 없거나 자격증명이 비어 있다. 보관본으로 진행된 것이며 매핑 측정치는 유효하다 |
| Gemini 429 | 무료 할당량 소진. 오픈 모델로 전환하거나 `LLM_MODEL` 을 바꾼다 |

## 구조

폴더 구조와 각 폴더의 책임은 [AGENTS.md](AGENTS.md) §3, §4를 참조한다. `data/normalized/`, `ontology/generated/`, `schemas/generated/`는 스크립트 생성물 폴더이며 직접 수정하지 않는다.

## License

[MIT License](LICENSE.md) — Copyright (c) 2026 Korean Register (KR)

## Notices

Project funding acknowledgements and third-party rights notices are
provided in [NOTICE.md](NOTICE.md).
