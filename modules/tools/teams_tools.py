"""Teams/chat MCP tool wrappers."""

from __future__ import annotations

import json
from typing import Any, Callable

from modules.enums import ContentType


def register_teams_tools(
    *,
    mcp: Any,
    get_singleton_client: Callable[[], Any],
    personal_assistant_provider: Callable[[], Any],
    error_payload: Callable[..., str],
):
    @mcp.tool()
    async def get_teams_chats(top: int = 25) -> str:
        """Get the user's recent Teams chat threads."""
        if top < 1 or top > 200:
            return error_payload("top must be between 1 and 200.")

        client = get_singleton_client()
        results = await personal_assistant_provider().get_teams_chats(client, top=top)
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    async def get_chat_messages(chat_id: str, top: int = 25) -> str:
        """Get messages from a specific Teams chat."""
        if not chat_id.strip():
            return error_payload("chat_id is required.")
        if top < 1 or top > 200:
            return error_payload("top must be between 1 and 200.")

        client = get_singleton_client()
        results = await personal_assistant_provider().get_chat_messages(client, chat_id=chat_id, top=top)
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    async def get_chat_participants(chat_id: str) -> str:
        """Get participant identities for a specific Teams chat."""
        if not chat_id.strip():
            return error_payload("chat_id is required.")

        client = get_singleton_client()
        result = await personal_assistant_provider().get_chat_participants(client, chat_id=chat_id)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def send_chat_message(
        message: str,
        recipient: str | None = None,
        chat_id: str | None = None,
        content_type: str = ContentType.TEXT.value,
    ) -> str:
        """Send a Teams chat message to a user or existing chat.

        Example:
            >>> await send_chat_message(message=\"Can we talk at 2pm?\", recipient=\"nina@contoso.com\")
        """
        if not message.strip():
            return error_payload("message is required.")
        if not recipient and not chat_id:
            return error_payload("Either recipient or chat_id is required.")
        if recipient is not None and not recipient.strip():
            return error_payload("recipient must be a non-empty string when provided.")
        if chat_id is not None and not chat_id.strip():
            return error_payload("chat_id must be a non-empty string when provided.")
        normalized_content_type = content_type.strip().lower()
        if normalized_content_type not in {item.value for item in ContentType}:
            return error_payload("content_type must be one of: text, html.")

        client = get_singleton_client()
        result = await personal_assistant_provider().send_chat_message(
            client,
            message=message,
            recipient=recipient,
            chat_id=chat_id,
            content_type=normalized_content_type,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def send_channel_message(
        team_id: str,
        channel_id: str,
        message: str,
        content_type: str = ContentType.TEXT.value,
    ) -> str:
        """Send a message to a Microsoft Teams channel."""
        if not team_id.strip():
            return error_payload("team_id is required.")
        if not channel_id.strip():
            return error_payload("channel_id is required.")
        if not message.strip():
            return error_payload("message is required.")
        normalized_content_type = content_type.strip().lower()
        if normalized_content_type not in {item.value for item in ContentType}:
            return error_payload("content_type must be one of: text, html.")

        client = get_singleton_client()
        result = await personal_assistant_provider().send_channel_message(
            client,
            team_id=team_id,
            channel_id=channel_id,
            message=message,
            content_type=normalized_content_type,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def get_teams_and_channels() -> str:
        """List the user's joined Teams and their channels."""
        client = get_singleton_client()
        results = await personal_assistant_provider().get_teams_and_channels(client)
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    async def get_user_presence(user_ids: list[str] | None = None) -> str:
        """Get the presence status for the current user or specified users."""
        if user_ids is not None:
            if not user_ids:
                return error_payload("user_ids must include at least one user id when provided.")
            if any(not user_id.strip() for user_id in user_ids):
                return error_payload("user_ids must contain non-empty values.")

        client = get_singleton_client()
        results = await personal_assistant_provider().get_user_presence(client, user_ids=user_ids)
        return json.dumps(results, indent=2, default=str)

    return {
        "get_teams_chats": get_teams_chats,
        "get_chat_messages": get_chat_messages,
        "get_chat_participants": get_chat_participants,
        "send_chat_message": send_chat_message,
        "send_channel_message": send_channel_message,
        "get_teams_and_channels": get_teams_and_channels,
        "get_user_presence": get_user_presence,
    }
