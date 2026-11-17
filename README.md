# k-mds

Korea Maritime Data Space — IMO Compendium 참조모델 기반 해사 데이터 상호운용 플랫폼.

선박이 보내는 운항·연료·배출 보고 데이터를 **IMO Compendium 데이터 번호로 매핑·검증**하고, 표준모델 데이터베이스에 적재한 뒤 **정합성(ISO/IEC 25023 기준 측정치)을 자동 판정**한다.
LLM 은 매핑 후보 제안에만 쓰이고 최종 판정은 결정론 검증기가 한다.

## 구성

| 구성요소 | 경로 | 역할 | 포트 |
| --- | --- | --- | --- |
| GHG AI Agent | `apps/kr-ghg-ai-agent` | 수신 데이터를 IMO Compendium 으로 매핑·검증 | 8001 |
| 매핑 검증기 | `apps/imo-compendium-mapping-validator` | 참조모델 레지스트리와 결정론 검증 스킬 | (라이브러리) |
| K-MDS GHG Verifier | `apps/data-space` | 표준모델 API 와 포털(선박 목록, 정합성 대조, 챗봇, 대시보드) | 8088 / 3031 |
| 실증 하네스 | `verification/automation` | 실증 단계 실행, 측정치 M2·M3·M4, 판정 보고서·증적 | 8090 |
| n8n 워크플로 | `verification/automation/n8n` | 웹훅 자동화, 대화형 AI Agent | 5678 |

흐름: 데이터 제공자(IDS Provider) → K-MDS IDS Consumer → GHG AI Agent → GHG Verifier(표준모델) → 정합성 판정·보고서.

## 빠른 시작

요구사항: Docker(compose v2), git. 이미지 빌드에 인터넷이 필요하다.

```bash
git clone https://github.com/kr-woojj/k-mds.git && cd k-mds
cp .env.example .env     # 설명을 보고 값을 채운다 (커밋되지 않는다)
```

1. 저장소에 없는 준비물(IMO Compendium 원본 등)을 둔다. 목록과 생성 절차는 [DEPLOY.md](verification/automation/DEPLOY.md) §1~§2.
2. 기동한다.

   ```bash
   docker compose -f apps/data-space/compose.yaml up -d --build
   docker compose --env-file .env -f verification/automation/compose.yaml up -d --build
   curl http://localhost:8001/ready     # "status":"READY"
   curl http://localhost:8090/health    # "status":"ok"
   ```

3. n8n 을 띄우고 `verification/automation/n8n/*.json` 을 가져와 활성화한다(DEPLOY.md §5).
4. 실증을 실행한다.

   ```bash
   curl -X POST http://localhost:5678/webhook/kmds-s11 -H "content-type: application/json" -d "{\"skip_ids\": true}"
   ```

   응답의 `verdict` 와 `measures`(M2 매핑 완결성, M3 검증 정확성, M4 정합율)를 본다. 증적은 `verification/evidence/C02/s11/run_NN/`, 화면은 포털 <http://localhost:3031>.

AI 코딩 도구로 설치·검증을 맡기려면 [docs/AI_SETUP_PROMPT.md](docs/AI_SETUP_PROMPT.md) 의 지시문을 준다.

## LLM 선택

`.env` 의 `LLM_PROVIDER` 로 고른다. 기본은 `mock`(외부 호출 없음)이다.

| 구성 | 환경변수 |
| --- | --- |
| mock | `LLM_PROVIDER=mock` |
| 오픈 모델 (OpenAI 호환: vLLM, Ollama, LM Studio 등) | `LLM_PROVIDER=openai`, `LLM_MODEL`, `LLM_ENDPOINT`, `OPENAI_API_KEY` |

오픈 모델 서버는 `/v1/chat/completions` 와 구조화 출력(`response_format: json_schema`)을 지원해야 한다.
챗봇에 필요한 tool calling 을 서버가 지원하지 않으면 함께 뜨는 tool-call 프록시(:8091)를 거친다(DEPLOY.md §5).

## 환경변수와 비밀정보

실제 값은 저장소 루트의 `.env` 한 곳에만 둔다. 변수 설명은 `.env.example` 에 있다. 로그·증적·커밋 메시지에 값을 적지 않는다.

```bash
git config core.hooksPath scripts/githooks          # 커밋 전 비밀정보 검사 (클론마다 한 번)
uv run python scripts/check_secrets.py --staged     # 수동 검사
```

## 개발

요구사항: Python 3.11, [uv](https://docs.astral.sh/uv/). 검증 명령은 `scripts/dev.py` 하나로 실행하며 CI 도 같은 명령을 쓴다.

```bash
uv sync
uv run python scripts/dev.py build      # 컴파일·import 검증
uv run python scripts/dev.py validate   # Ruff + MyPy + Pytest
```

폴더 구조와 개발 규약은 [AGENTS.md](AGENTS.md)를 따른다. `data/normalized/`, `ontology/generated/`, `schemas/generated/` 는 생성물이므로 직접 고치지 않는다.

## 운영 수칙

- 컨테이너 실행 중에는 호스트에서 `apps/kr-ghg-ai-agent` 의 테스트를 돌리지 않는다(레지스트리 SQLite 잠금 경합).
- 증적 폴더 `run_NN` 은 덮어쓰지 않는다. 실선 데이터와 참여기관 인프라 주소가 든 증적은 저장소에 올리지 않는다.
- 데이터 초기화와 백업은 DEPLOY.md §7.

## 문제 해결

| 증상 | 조치 |
| --- | --- |
| `/ready` 의 `llm.real` 이 false | `.env` 의 `LLM_PROVIDER`·키를 확인하고 `--env-file .env` 로 에이전트를 다시 띄운다 |
| 증적에 `LLM_OUTPUT_INVALID` | 모델이 구조화 출력을 지키지 못했다. 해당 필드는 미매핑으로 남는다. `LLM_DISABLE_THINKING=true` 를 써 본다 |
| 챗봇이 `Error in workflow` | n8n 자격증명의 Base URL 을 프록시(`http://host.docker.internal:8091/v1`)로 두고 `curl localhost:8091/health` 를 확인한다 |
| `verdict` 가 PARTIAL 이고 IDS 전달만 false | IDS Provider 에 데이터가 없거나 자격증명이 비었다. 보관본으로 진행된 것이며 매핑 측정치는 유효하다 |

## License

[MIT License](LICENSE.md) — Copyright (c) 2026 Korean Register (KR). 과제 사사와 제3자 권리 고지는 [NOTICE.md](NOTICE.md).
