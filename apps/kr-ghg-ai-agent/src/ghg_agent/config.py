"""환경 설정.

env 규약은 kr-ai-agents/lab/select_model.py 에서 확인된 이름을 우선 따른다
(AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT,
AZURE_OPENAI_API_VERSION, OPENAI_API_KEY, OPENAI_BASE_URL). 그 위에 본
PoC 지시서의 LLM_* 변수를 우선순위 높은 override 로 둔다.

비밀 값은 어디에도 로깅하지 않는다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _bounded_int(name: str, default: int, floor: int, ceil: int) -> int:
    """env 정수 값을 [floor, ceil] 로 clamp 한다 — 환경변수로 방어를 무력화할 수 없다."""
    raw = _env(name)
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return min(max(value, floor), ceil)


@dataclass(frozen=True)
class Settings:
    # LLM
    llm_provider: str = "mock"  # azure_openai | openai | gemini | mock
    llm_model: str = ""
    llm_deployment: str = ""
    llm_endpoint: str = ""
    llm_api_version: str = ""
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2
    allow_live_llm: bool = False
    # 오픈 모델(OpenAI 호환 서버, 예: vLLM 의 Qwen3) 전용 옵션 — 매핑은 결정론 파이프라인이 지배하므로
    # 사고(thinking) 과정을 끄고 추론 강도를 낮춰 지연을 줄인다. 상용 provider 에는 전달하지 않는다.
    llm_disable_thinking: bool = False
    llm_reasoning_effort: str = ""  # low | medium | xhigh (서버 기본값은 비움)

    # Skill / Reference
    imo_mapping_skill_path: Path = PROJECT_ROOT.parent / "imo-compendium-mapping-validator"
    registry_db_path: Path = PROJECT_ROOT / "var" / "registry.sqlite3"
    code_lists_path: Path = PROJECT_ROOT / "var" / "reference" / "code_lists.json"
    alias_config_path: Path = PROJECT_ROOT / "src" / "ghg_agent" / "reference" / "aliases.json"
    candidate_inventory_path: Path = PROJECT_ROOT / "var" / "candidate-inventory.json"
    # LAB021(vessellink) Provider 코드북 — 결정 D4(2026-09-26): 코드북 사전 정규화를 에이전트 ingress 에 내장.
    lab021_codebook_path: Path = PROJECT_ROOT / "var" / "reference" / "lab021" / "noon-code-book.json"
    skill_timeout_seconds: float = 60.0

    # MCP
    mcp_mode: str = "off"  # off | stdio
    mcp_server_command: str = ""
    mcp_server_args: tuple[str, ...] = field(default_factory=tuple)

    # KR GEARs
    kr_gears_delivery_mode: str = "mock"  # mock | http
    kr_gears_api_url: str = ""

    # Evidence / 정책
    audit_log_dir: Path = PROJECT_ROOT / "evidence"
    mapping_confidence_threshold: float = 0.90
    synthetic_data: bool = True

    # Ingress resource limits (F-STEP6-1) — wide payload fail-closed
    max_node_count: int = 3000
    max_array_length: int = 1000
    max_field_count: int = 2000
    max_scalar_text_length: int = 8192


def load_settings() -> Settings:
    return Settings(
        llm_provider=_env("LLM_PROVIDER", "mock"),
        llm_model=_env("LLM_MODEL") or _env("OPENAI_DEPLOYMENT"),
        llm_deployment=_env("LLM_DEPLOYMENT") or _env("AZURE_OPENAI_DEPLOYMENT"),
        llm_endpoint=_env("LLM_ENDPOINT") or _env("AZURE_OPENAI_ENDPOINT"),
        llm_api_version=_env("LLM_API_VERSION") or _env("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        llm_timeout_seconds=float(_env("LLM_TIMEOUT_SECONDS", "60")),
        llm_max_retries=int(_env("LLM_MAX_RETRIES", "2")),
        allow_live_llm=_env("ALLOW_LIVE_LLM", "false").lower() == "true",
        llm_disable_thinking=_env("LLM_DISABLE_THINKING", "false").lower() == "true",
        llm_reasoning_effort=_env("LLM_REASONING_EFFORT"),
        imo_mapping_skill_path=Path(
            _env("IMO_MAPPING_SKILL_PATH")
            or str(PROJECT_ROOT.parent / "imo-compendium-mapping-validator")
        ),
        registry_db_path=Path(
            _env("REGISTRY_DB_PATH") or str(PROJECT_ROOT / "var" / "registry.sqlite3")
        ),
        code_lists_path=Path(
            _env("K_MDS_REFERENCE_PATH")
            or str(PROJECT_ROOT / "var" / "reference" / "code_lists.json")
        ),
        candidate_inventory_path=Path(
            _env("CANDIDATE_INVENTORY_PATH")
            or str(PROJECT_ROOT / "var" / "candidate-inventory.json")
        ),
        lab021_codebook_path=Path(
            _env("LAB021_CODEBOOK_PATH")
            or str(PROJECT_ROOT / "var" / "reference" / "lab021" / "noon-code-book.json")
        ),
        skill_timeout_seconds=float(_env("SKILL_TIMEOUT_SECONDS", "60")),
        mcp_mode=_env("MCP_TRANSPORT", "off"),
        mcp_server_command=_env("MCP_SERVER_COMMAND"),
        mcp_server_args=tuple(a for a in _env("MCP_SERVER_ARGS").split() if a),
        kr_gears_delivery_mode=_env("KR_GEARS_DELIVERY_MODE", "mock"),
        kr_gears_api_url=_env("KR_GEARS_API_URL"),
        audit_log_dir=Path(_env("AUDIT_LOG_DIR") or str(PROJECT_ROOT / "evidence")),
        mapping_confidence_threshold=float(_env("MAPPING_CONFIDENCE_THRESHOLD", "0.90")),
        max_node_count=_bounded_int("MAX_NODE_COUNT", 3000, 100, 100000),
        max_array_length=_bounded_int("MAX_ARRAY_LENGTH", 1000, 10, 50000),
        max_field_count=_bounded_int("MAX_FIELD_COUNT", 2000, 50, 50000),
        max_scalar_text_length=_bounded_int("MAX_SCALAR_TEXT_LENGTH", 8192, 256, 1048576),
    )
