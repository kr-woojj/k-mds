"""`.env` 와 `.env.example` 정리: 쓰지 않는 LLM 제공자 키 항목을 지우고, 변수마다 설명 주석을 붙인다.

값은 읽지도 출력하지도 않는다(줄 단위로 변수 이름만 본다). 여러 번 돌려도 결과가 같다.
사용: python scripts/tidy_env.py [파일 ...]   (기본: .env .env.example)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# 현재 구성(오픈 모델, OpenAI 호환)에서 쓰지 않는 LLM 제공자 전용 항목. OPENAI_* 는 오픈 모델 연결에 쓰므로 남긴다.
UNUSED_LLM = re.compile(r"^(GEMINI|GOOGLE|AZURE_OPENAI|ANTHROPIC|CLAUDE|COHERE|MISTRAL|GROQ|TOGETHER|PERPLEXITY|XAI|DEEPSEEK|UPSTAGE|HUGGINGFACE|HF)_"
                        r"|^OPENAI_DEPLOYMENT$|^LLM_DEPLOYMENT$|^LLM_API_VERSION$")

DESC = {
    "LLM_PROVIDER": "언어 모델 연결 방식: mock(외부 호출 없음) | openai(OpenAI 호환 서버, 오픈 모델)",
    "LLM_MODEL": "서버가 요구하는 모델 호출명",
    "LLM_ENDPOINT": "언어 모델 서버 주소 (예: http://<host>:<port>/v1). tool-call 프록시의 상위 주소로도 쓴다",
    "LLM_DISABLE_THINKING": "true 면 모델의 사고 과정 출력을 끈다(응답이 빨라진다)",
    "LLM_REASONING_EFFORT": "추론 강도: low | medium | xhigh. 비우면 서버 기본값",
    "LLM_TIMEOUT_SECONDS": "언어 모델 호출 제한 시간(초)",
    "LLM_MAX_RETRIES": "언어 모델 호출 재시도 횟수",
    "ALLOW_LIVE_LLM": "true 일 때만 실제 언어 모델을 호출한다. 그 외에는 mock",
    "OPENAI_API_KEY": "오픈 모델 서버(OpenAI 호환)가 발급한 키. n8n 자격증명에도 같은 값을 쓴다",
    "OPENAI_BASE_URL": "OpenAI 호환 클라이언트의 기본 주소. 보통 LLM_ENDPOINT 와 같다",
    "UPSTREAM_BASE": "tool-call 프록시가 넘겨줄 상위 모델 서버 주소(비우면 LLM_ENDPOINT)",
    "UPSTREAM_API_KEY": "tool-call 프록시가 상위 서버에 쓸 키(비우면 요청의 키를 그대로 전달)",
    "UPSTREAM_TIMEOUT_SECONDS": "tool-call 프록시의 상위 호출 제한 시간(초)",
    "PROXY_PORT": "tool-call 프록시 포트",
    "IDS_CONNECTOR_BASE": "K-MDS IDS Consumer 커넥터 API 주소 (https://<host>:<port>)",
    "IDS_CONNECTOR_USER": "IDS Consumer 커넥터 계정",
    "IDS_CONNECTOR_PASSWORD": "IDS Consumer 커넥터 비밀번호",
    "IDS_NOON_ARTIFACT_ID": "수신할 Noon Report artifact ID. 비우면 시험용 기본 artifact",
    "S11_EVIDENCE_DIR": "S-1-1 증적 저장 폴더. 실선 데이터는 verification/evidence-private/ 아래를 지정한다",
    "KMDS_ENV_FILE": "run_s11 이 읽을 환경 파일 경로(기본: 저장소 루트 .env)",
    "IMO_API_KEY": "매핑 검증 서비스(imo-compendium-mapping-validator) API 키",
    "IMO_MAPPING_SKILL_PATH": "매핑 검증 도구 폴더 경로(기본: 형제 폴더)",
    "REGISTRY_DB_PATH": "IMO Compendium 참조 registry(sqlite) 경로",
    "K_MDS_REFERENCE_PATH": "코드 목록 파일 경로",
    "CANDIDATE_INVENTORY_PATH": "언어 모델에 제시할 후보 집합 파일 경로",
    "LAB021_CODEBOOK_PATH": "제공자(vessellink) 코드북 파일 경로",
    "AUDIT_LOG_DIR": "에이전트 증적 저장 폴더",
    "MAPPING_CONFIDENCE_THRESHOLD": "언어 모델 후보를 받아들이는 최소 점수(기본 0.90)",
    "SKILL_TIMEOUT_SECONDS": "매핑 검증 도구 호출 제한 시간(초)",
    "MCP_TRANSPORT": "MCP 경로: off | stdio (선택 기능)",
    "MCP_SERVER_COMMAND": "MCP 서버 실행 명령",
    "MCP_SERVER_ARGS": "MCP 서버 실행 인자(공백 구분)",
    "KR_GEARS_DELIVERY_MODE": "검증 시스템 전달 방식: mock 만 지원(실제 제출 없음)",
    "KR_GEARS_API_URL": "검증 시스템 API 주소(PoC 에서는 쓰지 않는다)",
    "SHIP_ODMS_BASE": "표준모델 API(GHG Verifier 백엔드) 주소",
    "AGENT_BASE": "GHG AI Agent 주소(하네스가 호출)",
    "AGENT_INBOX": "하네스가 읽는 에이전트 증적 폴더",
}
KEY = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
# 주석·예시 값에 남은 특정 모델 이름과 옛 프록시 이름을 일반 용어로 바꾼다(변수 값은 건드리지 않는다: 주석 줄에만 적용).
SCRUB = [(re.compile(r"의 Qwen[0-9.]*-?[0-9A-Za-z]* \(vLLM, 호출명 qwen, "), " (vLLM, "), (re.compile(r"Qwen[0-9.]* 등 사고\(thinking\) 모델"), "사고(thinking)형 모델"),
         (re.compile(r"\. 예 qwen>"), ">"), (re.compile(r"qwen-tool-proxy"), "tool-call-proxy"), (re.compile(r"Qwen[0-9.]*(-[0-9A-Za-z]+)?"), "오픈 모델")]


def tidy(path: Path) -> tuple[int, int, int]:
    out: list[str] = []
    removed = described = unknown = 0
    for line in path.read_text("utf-8").splitlines():
        m = KEY.match(line)
        if not m or line.lstrip().startswith("#"):
            if line.lstrip().startswith("#"):
                for pat, rep in SCRUB:
                    line = pat.sub(rep, line)
            if m and UNUSED_LLM.search(m.group(1)):
                continue  # 주석 처리된 예시 항목이라도 쓰지 않는 제공자 것은 지운다
            out.append(line)
            continue
        name = m.group(1)
        if UNUSED_LLM.search(name):
            removed += 1
            while out and out[-1].lstrip().startswith("#") and name.split("_")[0].lower() in out[-1].lower():
                out.pop()  # 그 항목만 설명하던 바로 위 주석도 함께 지운다
            continue
        desc = DESC.get(name)
        if desc is None:
            unknown += 1
        elif not (out and out[-1].strip() == f"# {desc}"):
            out.append(f"# {desc}")
            described += 1
        out.append(line)
    path.write_text("\n".join(out) + "\n", "utf-8")
    return removed, described, unknown


if __name__ == "__main__":
    for arg in sys.argv[1:] or [".env", ".env.example"]:
        p = Path(arg)
        if not p.is_file():
            print(f"{arg}: 없음")
            continue
        r, d, u = tidy(p)
        print(f"{arg}: 삭제 {r}줄, 설명 추가 {d}개, 설명 없는 변수 {u}개")
