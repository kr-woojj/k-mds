"""OpenAI 호환 오픈 모델 서버(vLLM Qwen3)용 tool-call 파서 우회 프록시.

서버가 `--enable-auto-tool-choice --tool-call-parser` 없이 떠 있으면 `tools` 가 든 요청은
400 으로 거절된다("auto" tool choice requires …). 그러나 `tool_choice: "none"` 으로 보내면
서버가 도구 목록을 프롬프트에 넣어 주고, 모델은 Qwen3 고유 형식으로 답한다:

    <tool_call>
    <function=NAME>
    <parameter=KEY>
    VALUE
    </parameter>
    </function>
    </tool_call>

이 프록시는 (1) 요청의 tool_choice 를 "none" 으로 바꿔 전달하고, (2) 응답 본문의 <tool_call>
블록을 OpenAI `tool_calls` 로 바꿔 돌려준다. n8n OpenAI Chat Model 노드·LangChain 등
OpenAI 규약 클라이언트가 그대로 동작한다.
덤으로 Qwen3 의 사고 과정(enable_thinking)과 추론 강도(reasoning_effort)를 env 로 고정한다.

표준 라이브러리만 쓴다. 비밀 값(키)은 클라이언트 Authorization 헤더를 그대로 전달하며
기록하지 않는다.

env: UPSTREAM_BASE(필수, 예 http://host:port/v1) · PROXY_PORT(기본 8091)
     · LLM_DISABLE_THINKING(기본 true) · LLM_REASONING_EFFORT(기본 비움)
     · UPSTREAM_API_KEY(선택: 클라이언트가 키를 안 보낼 때 대신 사용)
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

UPSTREAM = os.environ.get("UPSTREAM_BASE", "").rstrip("/")
PORT = int(os.environ.get("PROXY_PORT", "8091"))
DISABLE_THINKING = os.environ.get("LLM_DISABLE_THINKING", "true").lower() == "true"
REASONING_EFFORT = os.environ.get("LLM_REASONING_EFFORT", "").strip()
FALLBACK_KEY = os.environ.get("UPSTREAM_API_KEY", "")
TIMEOUT = float(os.environ.get("UPSTREAM_TIMEOUT_SECONDS", "300"))

_BLOCK = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.S)
_FUNC = re.compile(r"<function=([^>\s]+)>\s*(.*?)\s*</function>", re.S)
_PARAM = re.compile(r"<parameter=([^>\s]+)>\s*(.*?)\s*</parameter>", re.S)


def _coerce(value: str, schema: dict[str, Any] | None) -> Any:
    """파라미터 문자열을 도구 JSON schema 의 타입으로 바꾼다. 모르면 문자열 그대로."""
    t = (schema or {}).get("type")
    v = value.strip()
    if t == "boolean":
        return v.lower() in ("true", "1", "yes")
    if t == "integer":
        try:
            return int(v)
        except ValueError:
            return v
    if t == "number":
        try:
            return float(v)
        except ValueError:
            return v
    if t in ("object", "array"):
        try:
            return json.loads(v)
        except ValueError:
            return v
    if v.lower() in ("null", "none") and schema and schema.get("nullable"):
        return None
    return v


def parse_tool_calls(content: str, tools: list[dict[str, Any]]) -> tuple[str | None, list[dict[str, Any]]]:
    """본문에서 <tool_call> 블록을 떼어 OpenAI tool_calls 로 만든다. 남는 글은 content 로 돌려준다."""
    schemas = {t["function"]["name"]: t["function"].get("parameters", {}).get("properties", {})
               for t in tools if t.get("type") == "function"}
    calls: list[dict[str, Any]] = []
    for block in _BLOCK.findall(content):
        for name, body in _FUNC.findall(block):
            args = {k: _coerce(v, schemas.get(name, {}).get(k)) for k, v in _PARAM.findall(body)}
            calls.append({"id": f"call_{uuid.uuid4().hex[:12]}", "type": "function",
                          "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}})
    rest = _BLOCK.sub("", content).strip()
    return (rest or None), calls


def _upstream(path: str, method: str, body: bytes | None, auth: str | None) -> tuple[int, dict[str, str], bytes]:
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = auth
    elif FALLBACK_KEY:
        headers["Authorization"] = f"Bearer {FALLBACK_KEY}"
    req = urllib.request.Request(UPSTREAM + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        # 업스트림 서버가 닫혀 있거나 응답이 없을 때 — 연결을 끊지 않고 502 JSON 으로 알린다
        msg = {"error": {"message": f"upstream unreachable: {type(e).__name__}: {e}", "type": "upstream_error", "code": 502}}
        return 502, {}, json.dumps(msg, ensure_ascii=False).encode("utf-8")


def transform_request(body: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], bool]:
    tools = body.get("tools") or []
    want_stream = bool(body.get("stream"))
    out = dict(body)
    out["stream"] = False
    out.pop("stream_options", None)
    if tools:
        out["tool_choice"] = "none"          # 서버 파서 없이도 템플릿이 도구를 프롬프트에 넣는다
        out.pop("parallel_tool_calls", None)
    else:
        out.pop("tool_choice", None)
    ctk = dict(out.get("chat_template_kwargs") or {})
    if DISABLE_THINKING and "enable_thinking" not in ctk:
        ctk["enable_thinking"] = False
    if ctk:
        out["chat_template_kwargs"] = ctk
    if REASONING_EFFORT and "reasoning_effort" not in out:
        out["reasoning_effort"] = REASONING_EFFORT
    return out, tools, want_stream


def transform_response(resp: dict[str, Any], tools: list[dict[str, Any]]) -> dict[str, Any]:
    for choice in resp.get("choices", []):
        msg = choice.get("message") or {}
        content = msg.get("content") or ""
        if tools and "<tool_call>" in content:
            rest, calls = parse_tool_calls(content, tools)
            if calls:
                msg["content"] = rest
                msg["tool_calls"] = calls
                choice["finish_reason"] = "tool_calls"
        msg.pop("reasoning_content", None)   # 사고 내용은 클라이언트로 보내지 않는다
        choice["message"] = msg
    return resp


def to_sse(resp: dict[str, Any]) -> bytes:
    """비스트리밍 응답을 SSE 한 덩어리로 바꾼다(클라이언트가 stream=true 를 요구했을 때)."""
    out = []
    for choice in resp.get("choices", []):
        msg = choice.get("message", {})
        delta: dict[str, Any] = {"role": "assistant", "content": msg.get("content")}
        if msg.get("tool_calls"):
            delta["tool_calls"] = [{"index": i, **tc} for i, tc in enumerate(msg["tool_calls"])]
        chunk = {"id": resp.get("id"), "object": "chat.completion.chunk", "created": resp.get("created"), "model": resp.get("model"),
                 "choices": [{"index": choice.get("index", 0), "delta": delta, "finish_reason": None}]}
        out.append(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n")
        fin = {**chunk, "choices": [{"index": choice.get("index", 0), "delta": {}, "finish_reason": choice.get("finish_reason")}], "usage": resp.get("usage")}
        out.append(f"data: {json.dumps(fin, ensure_ascii=False)}\n\n")
    out.append("data: [DONE]\n\n")
    return "".join(out).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "qwen-tool-proxy/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:   # 기본 로그는 경로만, 본문·헤더는 남기지 않는다
        sys.stderr.write("%s - %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def _send(self, status: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/health", "/"):
            self._send(200, json.dumps({"status": "ok", "upstream": bool(UPSTREAM), "disable_thinking": DISABLE_THINKING,
                                        "reasoning_effort": REASONING_EFFORT or None}).encode())
            return
        status, _, data = _upstream(self.path.replace("/v1", "", 1) if self.path.startswith("/v1") else self.path, "GET", None,
                                    self.headers.get("Authorization"))
        self._send(status, data)

    def do_POST(self) -> None:
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        path = self.path.replace("/v1", "", 1) if self.path.startswith("/v1") else self.path
        if path != "/chat/completions":
            status, _, data = _upstream(path, "POST", raw, self.headers.get("Authorization"))
            self._send(status, data)
            return
        try:
            body = json.loads(raw.decode("utf-8"))
        except ValueError:
            self._send(400, b'{"error":{"message":"invalid JSON"}}')
            return
        up_body, tools, want_stream = transform_request(body)
        status, _, data = _upstream(path, "POST", json.dumps(up_body, ensure_ascii=False).encode("utf-8"), self.headers.get("Authorization"))
        if status != 200:
            self._send(status, data)
            return
        resp = transform_response(json.loads(data.decode("utf-8")), tools)
        if want_stream:
            self._send(200, to_sse(resp), "text/event-stream")
        else:
            self._send(200, json.dumps(resp, ensure_ascii=False).encode("utf-8"))


def main() -> None:
    if not UPSTREAM:
        sys.exit("UPSTREAM_BASE 가 필요하다 (예: http://<host>:<port>/v1)")
    sys.stderr.write(f"qwen-tool-proxy :{PORT} → upstream 설정됨 | thinking off={DISABLE_THINKING} | effort={REASONING_EFFORT or '-'}\n")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
