"""Operability/domain tool wrappers extracted from main.py."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable


def register_operability_tools(
    *,
    mcp: Any,
    get_singleton_client: Callable[[], Any],
    personal_assistant_provider: Callable[[], Any],
    all_scopes: list[str],
    recommended_v2_scopes: list[str],
    tool_scope_map: dict[str, list[str]],
    v2_tool_names: set[str],
    resolve_tool_fn: Callable[[str], Any],
):
    """Register operability tools and return exported wrapper callables."""

    @mcp.tool()
    async def health_check() -> str:
        """Verify authentication and Graph connectivity.

        Example:
            >>> await health_check()
        """
        client = get_singleton_client()
        result = await personal_assistant_provider().health_check(client)
        if isinstance(result, dict):
            result.setdefault("version", 2)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def get_effective_scopes() -> str:
        """Return configured scopes and inferred missing recommended scopes.

        Example:
            >>> await get_effective_scopes()
        """
        configured_scopes = sorted(all_scopes)
        missing_recommended = [scope for scope in recommended_v2_scopes if scope not in configured_scopes]

        result = {
            "configured_scopes": configured_scopes,
            "granted_scopes": None,
            "missing_recommended_scopes": missing_recommended,
            "version": 2,
        }
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def list_supported_tools() -> str:
        """List supported MCP tools with scope mapping.

        Example:
            >>> await list_supported_tools()
        """
        tools = []
        for tool_name, required_scopes in sorted(tool_scope_map.items()):
            tool_fn = resolve_tool_fn(tool_name)
            if not callable(tool_fn):
                continue
            doc = (tool_fn.__doc__ or "").strip().splitlines()
            description = doc[0] if doc else ""
            tools.append(
                {
                    "name": tool_name,
                    "description": description,
                    "required_scopes": required_scopes,
                    "version": "2" if tool_name in v2_tool_names else "1",
                }
            )

        result = {
            "tools": tools,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "version": 2,
        }
        return json.dumps(result, indent=2, default=str)

    return {
        "health_check": health_check,
        "get_effective_scopes": get_effective_scopes,
        "list_supported_tools": list_supported_tools,
    }
