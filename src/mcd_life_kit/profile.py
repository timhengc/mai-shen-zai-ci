"""仅从明确的本人账号字段取展示名；不将账号 ID 或配送联系人冒充用户名。"""
from __future__ import annotations

import re
from typing import Any

from .mcp_client import MCPClient, MCPError

PROFILE_TOOLS = ("query-my-profile", "get-user-profile", "query-user-info", "query-member-info", "query-my-account")
NAME_KEYS = ("nickname", "nickName", "userNickName", "displayName", "userName", "username", "memberName")
PROFILE_KEYS = ("data", "profile", "userProfile", "memberProfile", "userInfo", "memberInfo")


def account_name(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("success") is False:
        return None
    if "code" in payload and str(payload["code"]) not in {"0", "200", "0000"}:
        return None
    for key in NAME_KEYS:
        value = payload.get(key)
        if isinstance(value, str):
            value = value.strip()
            if value and not re.fullmatch(r"(?:\+?86)?1[0-9*]{10}", value):
                return value
    for key in PROFILE_KEYS:
        name = account_name(payload.get(key))
        if name:
            return name
    return None


def fetch_account_name(client: MCPClient, tools: list[dict]) -> str | None:
    available = {tool["name"]:tool for tool in tools}
    for name in PROFILE_TOOLS:
        tool = available.get(name)
        if not tool or tool.get("inputSchema", {}).get("required"):
            continue
        try:
            result = account_name(client.call_tool(name, {}))
        except MCPError:
            continue
        if result:
            return result
    return None


def choose_display_name(explicit: str | None, fetched: str | None, fallback: str | None = None) -> tuple[str | None, str]:
    if explicit is not None:
        return explicit.strip() or None, "user" if explicit.strip() else "hidden"
    if fetched:
        return fetched, "account"
    if fallback and fallback.strip():
        return fallback.strip(), "fallback"
    return None, "hidden"
