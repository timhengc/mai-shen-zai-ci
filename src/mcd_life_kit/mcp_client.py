"""麦当劳 MCP 最小客户端（Streamable HTTP + JSON-RPC 2.0，仅标准库）。"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_ENDPOINT = "https://mcp.mcd.cn"
PROTOCOL_VERSION = "2025-06-18"


class MCPError(RuntimeError):
    """MCP 调用失败。"""


def read_token_file(path: Path) -> str:
    """显式账号文件只使用本文件凭证，支持 dotenv 与单行 Token，不回退到其他账号。"""
    content = path.read_text(encoding="utf-8-sig").strip()
    token = None
    recognized = False
    for line in content.splitlines():
        key, separator, value = line.strip().partition("=")
        if separator and key in {"MCD_MCP_TOKEN", "MCDONALDS_MCP_TOKEN"}:
            recognized = True
            value = value.strip().strip("\"'")
            if value:
                token = value
                break
    if not recognized and content and '=' not in content.rstrip('=') and not any(c.isspace() for c in content) and not content.startswith("#"):
        token = content
    if not token or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in token):
        raise ValueError("指定配置文件中没有有效 Token；请使用 MCD_MCP_TOKEN=... 或单行 Token。")
    return token


class MCPClient:
    def __init__(
        self,
        token: str | None = None,
        endpoint: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self.token = (
            token
            or os.environ.get("MCD_MCP_TOKEN")
            or os.environ.get("MCDONALDS_MCP_TOKEN")
            or ""
        )
        self.endpoint = (endpoint or os.environ.get("MCD_MCP_ENDPOINT") or DEFAULT_ENDPOINT).rstrip(
            "/"
        )
        self.timeout = timeout
        self.max_retries = max_retries
        self._session_id: str | None = None
        self._next_id = 0

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
            "User-Agent": "mcd-life-kit/0.1",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    def _rpc(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if not self.token:
            raise MCPError("缺少 MCP Token：请设置环境变量 MCD_MCP_TOKEN，或使用 --mock。")

        self._next_id += 1
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            payload["params"] = params

        data = json.dumps(payload).encode("utf-8")
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            request = urllib.request.Request(
                self.endpoint, data=data, headers=self._headers(), method="POST"
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    session_id = response.headers.get("Mcp-Session-Id")
                    if session_id:
                        self._session_id = session_id
                    body = response.read().decode("utf-8", errors="replace")
                return self._unwrap(self._parse_body(body))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
                if exc.code == 401:
                    raise MCPError(f"401：MCP Token 无效或已过期。{detail}") from exc
                if exc.code == 429:
                    last_error = MCPError("429：触发限流（600 次/分钟）。")
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise MCPError(f"HTTP {exc.code}：{detail or exc.reason}") from exc
            except urllib.error.URLError as exc:
                last_error = MCPError(f"网络错误：{exc.reason}")
                time.sleep(1.0 * (attempt + 1))

        raise last_error or MCPError("未知错误")

    @staticmethod
    def _parse_body(body: str) -> Any:
        text = body.strip()
        if not text:
            return {}
        if text.startswith("{"):
            return json.loads(text)
        result: Any = None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk and chunk != "[DONE]":
                    result = json.loads(chunk)
        if result is None:
            raise MCPError("无法解析 MCP 响应")
        return result

    @staticmethod
    def _unwrap(message: Any) -> Any:
        if isinstance(message, dict) and "error" in message:
            raise MCPError(json.dumps(message["error"], ensure_ascii=False))
        if isinstance(message, dict) and "result" in message:
            return message["result"]
        return message

    def list_tools(self) -> list[dict[str, Any]]:
        result = self._rpc("tools/list")
        return list((result or {}).get("tools") or [])

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        result = self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        if not isinstance(result, dict):
            return result

        if result.get("isError"):
            raise MCPError(f"MCP 工具 {name} 执行失败，请检查参数与账户状态。")

        structured = result.get("structuredContent")
        if isinstance(structured, (dict, list)) and structured:
            return structured

        texts: list[str] = []
        for block in result.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(str(block.get("text") or ""))
        blob = "\n".join(texts).strip()
        if not blob:
            return result
        parsed = _extract_json(blob)
        return parsed if parsed is not None else blob


def _extract_json(text: str) -> Any:
    marker = "Original Response"
    index = text.find(marker)
    candidate = text[index + len(marker) :] if index >= 0 else text
    for anchor in ('{"success"', '{"code"', '{"data"', "{"):
        start = candidate.find(anchor)
        if start < 0:
            continue
        try:
            obj, _ = json.JSONDecoder().raw_decode(candidate[start:])
            return obj
        except json.JSONDecodeError:
            continue
    return None
