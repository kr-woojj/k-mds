"""IMO mapping Skill 을 노출하는 MCP stdio server.

패턴 근거: kr-ai-agents/lab/tavily_server.py 등 (mcp.server.fastmcp.FastMCP).
tool 이름·설명·입력 스키마는 validator 의 MappingToolkit.list_tools() 에서
런타임에 발견한 것을 그대로 등록한다 — 이름을 발명하지 않는다 (C-3).

실행:
  uv run python tools/mcp_server.py   (stdio transport)

환경변수:
  IMO_MAPPING_SKILL_PATH, REGISTRY_DB_PATH  (기본값: config.py 참조)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from ghg_agent.adapters.skill_adapter import ImoMappingSkillAdapter  # noqa: E402
from ghg_agent.config import load_settings  # noqa: E402


def build_server() -> FastMCP:
    settings = load_settings()
    adapter = ImoMappingSkillAdapter(
        skill_path=settings.imo_mapping_skill_path,
        registry_db_path=settings.registry_db_path,
        timeout_seconds=settings.skill_timeout_seconds,
    )
    server = FastMCP("imo-compendium-mapping-skill")

    # 런타임 discovery — validator 가 공표한 tool 만 등록한다.
    for tool_info in adapter.list_tools():
        tool_name = tool_info["name"]

        def _make(name: str):
            def _invoke(arguments: dict[str, Any]) -> dict[str, Any]:
                return adapter.invoke(name, arguments)

            return _invoke

        server.add_tool(
            _make(tool_name),
            name=tool_name,
            description=tool_info["description"],
        )

    @server.tool()
    def skill_readiness() -> dict[str, Any]:
        """Skill/Registry readiness와 버전 정보를 반환한다."""
        return adapter.readiness()

    return server


if __name__ == "__main__":
    build_server().run(transport="stdio")
