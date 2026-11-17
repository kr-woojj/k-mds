# GHG AI Agent 사용자 매뉴얼

버전 0.1.0 기준. 명령은 이 폴더(`apps/kr-ghg-ai-agent`)에서 실행한다. 구조와 설계는 [README.md](README.md)를 본다.

## 1. 준비물

- Python 3.12 이상과 `uv`, 또는 Docker
- 같은 저장소의 매핑 검증 도구 폴더 `apps/imo-compendium-mapping-validator`
- IMO Compendium 참조 데이터 파일(`data/raw/FAL50/IMO Compendium.xlsx`). 저장소에 포함되지 않으므로 따로 준비한다
- 제공자 코드북 파일(선박 플랫폼 형식을 쓸 때)

## 2. 설치

```bash
uv sync --python 3.12
uv run python tools/prepare_registry.py
```

두 번째 명령은 참조 데이터를 읽어 `var/registry.sqlite3` 를 만든다. 이 파일이 없으면 서버가 준비 상태가 되지 않는다.

## 3. 실행

로컬 실행:

```bash
PYTHONPATH=src uv run uvicorn --factory ghg_agent.api.app:create_app --port 8000
```

Docker 실행:

```bash
docker compose up --build
```

실행 후 확인:

| 주소 | 정상 응답 |
| --- | --- |
| `GET /health` | `{"status": "ok"}` |
| `GET /ready` | `READY` (구성 요소별 상태 포함. `DEGRADED`, `NOT_READY` 이면 4장의 설정을 확인한다) |

## 4. 설정 (환경변수)

비밀값은 `.env` 파일이나 실행 환경의 환경변수로 주고, 코드나 문서에 적지 않는다.

| 환경변수 | 기본값 | 설명 |
| --- | --- | --- |
| `LLM_PROVIDER` | `mock` | 언어 모델 연결 방식. `mock` 이면 외부 호출을 하지 않는다 |
| `LLM_MODEL`, `LLM_ENDPOINT` | 없음 | 언어 모델 이름과 서버 주소(OpenAI 호환) |
| `ALLOW_LIVE_LLM` | `false` | `true` 일 때만 실제 언어 모델을 호출한다 |
| `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES` | `60`, `2` | 호출 제한 시간과 재시도 횟수 |
| `IMO_MAPPING_SKILL_PATH` | 형제 폴더 | 매핑 검증 도구 폴더 경로 |
| `REGISTRY_DB_PATH` | `var/registry.sqlite3` | 참조 registry 파일 |
| `K_MDS_REFERENCE_PATH` | `var/reference/code_lists.json` | 코드 목록 파일 |
| `CANDIDATE_INVENTORY_PATH` | `var/candidate-inventory.json` | 후보 집합 파일 |
| `LAB021_CODEBOOK_PATH` | `var/reference/lab021/noon-code-book.json` | 제공자 코드북 파일 |
| `AUDIT_LOG_DIR` | `evidence` | 증적 저장 폴더 |
| `MAPPING_CONFIDENCE_THRESHOLD` | `0.90` | LLM 후보를 받아들이는 최소 점수 |
| `KR_GEARS_DELIVERY_MODE` | `mock` | 대상 시스템 전달 방식. 실제 제출은 지원하지 않는다 |
| `MCP_TRANSPORT` | `off` | MCP 경로 사용 여부(선택 기능) |

## 5. 사용 방법

### 5.1 보고 데이터 처리

수신부터 증적 생성까지 한 번에 수행한다.

```bash
curl -X POST http://localhost:8000/api/v1/ids/events \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/noon_report_valid.json
```

요청 본문에 `correlation_id` 가 있으면 그 값으로 증적 폴더가 만들어진다. 같은 `correlation_id` 로 다시 보내면 409 로 거부한다.

응답의 최종 상태:

| 상태 | 뜻 |
| --- | --- |
| `REVIEW_REQUIRED` | 처리는 끝났고 사람의 검토가 필요하다. 대상 시스템 계약이 잠정 상태라 정상 처리의 기본 결과다 |
| `FAILED` | 검증 실패나 구성 요소 장애로 중단됐다. 증적의 `validation-result.json` 을 확인한다 |

### 5.2 단계별 호출

| 엔드포인트 | 용도 |
| --- | --- |
| `POST /api/v1/map` | 필드 목록을 IMO 데이터 요소로 매핑한다 |
| `POST /api/v1/validate` | 매핑 결과를 검증한다 |
| `POST /api/v1/transform/kr-gears` | 검증된 결과를 대상 시스템 전달용 구조로 변환한다 |
| `GET /api/v1/runs/{correlation_id}` | 실행 결과와 증적 목록을 조회한다 |
| `GET /api/v1/governance` | 후보 집합과 참조 모델의 승인 상태를 조회한다 |

### 5.3 증적 확인

`evidence/{correlation_id}/` 폴더에 다음 파일이 생긴다.

| 파일 | 내용 |
| --- | --- |
| `manifest.json` | 실행 식별자, 코드 커밋, 참조 모델 버전, 실제/모의 구분, 파일별 해시 |
| `raw-input.json`, `raw-input.sha256` | 받은 원본과 해시 |
| `normalized-input.json` | 정규화된 입력 |
| `mapping-result.json` | 필드별 매핑 결과와 방법 |
| `validation-result.json` | 필드별 검증 판정 |
| `llm-calls.json`, `skill-calls.json` | 언어 모델과 검증 도구 호출 기록 |
| `kr-gears-output.json`, `delivery-result.json` | 변환·전달 결과(도달한 경우) |
| `summary.md` | 요약 |

## 6. 시험

```bash
uv run pytest tests/unit tests/contract -q     # 단위·계약 시험
uv run pytest tests/integration -q             # 통합 시험 (registry 준비 후)
uv run python tools/run_mock_e2e.py            # 모의 종단 시험 8개 시나리오
```

## 7. 문제 해결

| 증상 | 조치 |
| --- | --- |
| `REGISTRY_DB_NOT_FOUND` | `uv run python tools/prepare_registry.py` 를 먼저 실행한다 |
| `/ready` 가 `NOT_READY` | `IMO_MAPPING_SKILL_PATH` 와 registry 경로를 확인한다 |
| 409 `DUPLICATE_CORRELATION_ID` | 같은 식별자의 증적이 이미 있다. 새 식별자를 쓴다 |
| 실제 언어 모델 호출 실패 | `ALLOW_LIVE_LLM=true` 와 `LLM_ENDPOINT` 설정을 확인한다 |

## 8. 제한 사항

- 대상 검증 시스템의 제출 계약이 확정되지 않아 변환 결과는 잠정 상태이며, 실제 제출 기능은 없다.
- 단위 변환은 하지 않는다.
- 참조 모델에 대응 요소가 없는 항목은 매핑하지 않고 미매핑으로 남긴다.
- 개념 검증 단계의 프로그램이며 인증·암호화 통신은 적용하지 않았다.
