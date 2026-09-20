"""MCP client 어댑터 (D-4).

패턴 근거: kr-ai-agents/lab/build_agent.py 의 MultiServerMCPClient +
await client.get_tools() (langchain-mcp-adapters, stateless discovery).

- tool 이름은 discovery 결과만 사용한다 (하드코딩 금지).
- 모든 호출을 audit 기록한다 (server id, transport, tool, latency,
  sanitized arguments, correlation_id, real/mock).
- MCP 는 본 PoC 에서 optional 경로다: authoritative lookup 은 Python import
  Skill adapter 가 담당하므로 MCP 장애는 degraded 로 보고된다. MCP 를 유일한
  lookup 으로 구성하는 경우 장애 시 호출자는 REVIEW_REQUIRED/FAILED 로
  처리해야 한다 (C-5).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


class McpAdapterError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _sanitize_args(arguments: dict[str, Any], limit: int = 400) -> str:
    try:
        text = json.dumps(arguments, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        text = str(arguments)
    return text[:limit]


@dataclass
class McpCallRecord:
    server: str
    transport: str
    tool_name: str
    called_at: str
    latency_ms: float
    ok: bool
    error: str | None
    sanitized_arguments: str
    correlation_id: str | None
    real_call: bool


@dataclass
class McpSkillClient:
    """stdio MCP server 에 대한 discovery + 호출 클라이언트."""

    command: str
    args: tuple[str, ...]
    server_name: str = "imo-compendium-mapping-skill"
    transport: str = "stdio"
    real_call: bool = True
    call_log: list[McpCallRecord] = field(default_factory=list)
    _tools: dict[str, Any] | None = None

    def _client(self):
        from langchain_mcp_adapters.client import MultiServerMCPClient

        return MultiServerMCPClient(
            {
                self.server_name: {
                    "command": self.command,
                    "args": list(self.args),
                    "transport": "stdio",
                }
            }
        )

    async def discover(self) -> list[str]:
        """runtime tool discovery — 결과는 캐시할 수 있으나 추측하지 않는다."""
        started = time.perf_counter()
        error: str | None = None
        try:
            tools = await self._client().get_tools()
            self._tools = {tool.name: tool for tool in tools}
            return sorted(self._tools)
        except Exception as exc:
            error = type(exc).__name__
            raise McpAdapterError("MCP_DISCOVERY_ERROR", str(exc)) from exc
        finally:
            self.call_log.append(
                McpCallRecord(
                    server=self.server_name,
                    transport=self.transport,
                    tool_name="(discovery)",
                    called_at=datetime.now(UTC).isoformat(),
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                    ok=error is None,
                    error=error,
                    sanitized_arguments="",
                    correlation_id=None,
                    real_call=self.real_call,
                )
            )

    async def call(
        self, tool_name: str, arguments: dict[str, Any], correlation_id: str | None = None
    ) -> Any:
        if self._tools is None:
            await self.discover()
        assert self._tools is not None
        tool = self._tools.get(tool_name)
        if tool is None:
            raise McpAdapterError(
                "MCP_LOOKUP_ERROR", f"discovery 에 없는 tool: {tool_name}"
            )
        started = time.perf_counter()
        error: str | None = None
        try:
            result = await tool.ainvoke(arguments)
            return result
        except Exception as exc:
            error = type(exc).__name__
            raise McpAdapterError("MCP_LOOKUP_ERROR", str(exc)) from exc
        finally:
            self.call_log.append(
                McpCallRecord(
                    server=self.server_name,
                    transport=self.transport,
                    tool_name=tool_name,
                    called_at=datetime.now(UTC).isoformat(),
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                    ok=error is None,
                    error=error,
                    sanitized_arguments=_sanitize_args(arguments),
                    correlation_id=correlation_id,
                    real_call=self.real_call,
                )
            )

    def drain_call_log(self) -> list[dict[str, Any]]:
        drained = [vars(record) for record in self.call_log]
        self.call_log.clear()
        return drained
