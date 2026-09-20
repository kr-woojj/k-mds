"""TS-3: Real MCP(stdio) + Real Skill — runtime discovery 및 호출.

tools/mcp_server.py 를 실제 subprocess 로 띄워 MultiServerMCPClient 로
discovery/호출한다 (kr-ai-agents 의 stdio MCP 패턴).
"""

from __future__ import annotations

import sys

import pytest

from ghg_agent.adapters.mcp_adapter import McpSkillClient
from ghg_agent.config import PROJECT_ROOT
from tests.conftest import requires_registry, requires_skill

SERVER_SCRIPT = PROJECT_ROOT / "tools" / "mcp_server.py"

EXPECTED_TOOLS = {
    "map_dataset",
    "validate_mapping",
    "explain_mapping",
    "list_candidates",
    "compare_compendium_versions",
    "skill_readiness",
}


@pytest.fixture()
def mcp_client() -> McpSkillClient:
    return McpSkillClient(command=sys.executable, args=(str(SERVER_SCRIPT),))


@requires_registry
@requires_skill
class TestRealMcp:
    async def test_discovery_matches_skill_tools(self, mcp_client):
        tools = await mcp_client.discover()
        assert EXPECTED_TOOLS <= set(tools)
        record = mcp_client.call_log[-1]
        assert record.ok is True
        assert record.transport == "stdio"
        assert record.real_call is True

    async def test_validate_mapping_via_mcp(self, mcp_client):
        import json

        result = await mcp_client.call(
            "validate_mapping",
            {
                "arguments": {
                    "mappings": [
                        {
                            "field": {"name": "speed_through_water",
                                      "declared_type": "numeric"},
                            "imo_data_number": "IMO0616",
                        }
                    ]
                }
            },
            correlation_id="mcp-int-001",
        )
        if isinstance(result, list):
            result = result[0]
        if isinstance(result, dict) and "text" in result:
            result = result["text"]
        elif hasattr(result, "text"):
            result = result.text
        payload = json.loads(result) if isinstance(result, str) else result
        assert payload["ok"] is True
        assert payload["result"]["compendiumVersion"] == "FAL50"
        assert payload["result"]["overallStatus"] == "PASS"
        record = mcp_client.call_log[-1]
        assert record.tool_name == "validate_mapping"
        assert record.correlation_id == "mcp-int-001"
        assert record.ok is True
