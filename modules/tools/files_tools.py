"""Files/contacts MCP tool wrappers."""

from __future__ import annotations

import json
from typing import Any, Callable

from modules.enums import ShareLinkType, ShareLinkScope


def register_files_tools(
    *,
    mcp: Any,
    get_singleton_client: Callable[[], Any],
    personal_assistant_provider: Callable[[], Any],
    error_payload: Callable[..., str],
):
    @mcp.tool()
    async def get_contacts(top: int = 25) -> str:
        """Get the user's contacts from their address book."""
        if top < 1 or top > 200:
            return error_payload("top must be between 1 and 200.")

        client = get_singleton_client()
        results = await personal_assistant_provider().get_contacts(client, top=top)
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    async def get_recent_files(top: int = 25) -> str:
        """Get the user's recently accessed OneDrive files.

        Example:
            >>> await get_recent_files(top=10)
        """
        if top < 1 or top > 200:
            return error_payload("top must be between 1 and 200.")

        client = get_singleton_client()
        results = await personal_assistant_provider().get_recent_files(client, top=top)
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    async def search_files(query: str, top: int = 25) -> str:
        """Search for files in OneDrive and SharePoint by keyword."""
        if not query.strip():
            return error_payload("query is required.")
        if top < 1 or top > 200:
            return error_payload("top must be between 1 and 200.")

        client = get_singleton_client()
        results = await personal_assistant_provider().search_files(client, query=query, top=top)
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    async def list_drive_items(item_id: str | None = None, top: int = 50) -> str:
        """List OneDrive folder contents for root or a specific folder item ID."""
        if item_id is not None and not item_id.strip():
            return error_payload("item_id must be a non-empty string when provided.")
        if top < 1 or top > 200:
            return error_payload("top must be between 1 and 200.")

        client = get_singleton_client()
        result = await personal_assistant_provider().list_drive_items(client, item_id=item_id, top=top)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def create_share_link(
        item_id: str,
        link_type: str = ShareLinkType.VIEW.value,
        scope: str = ShareLinkScope.ORGANIZATION.value,
    ) -> str:
        """Create a share link for a OneDrive item."""
        if not item_id.strip():
            return error_payload("item_id is required.")

        normalized_link_type = link_type.strip().lower()
        if normalized_link_type not in {item.value for item in ShareLinkType}:
            return error_payload("link_type must be one of: view, edit.")

        normalized_scope = scope.strip().lower()
        if normalized_scope not in {item.value for item in ShareLinkScope}:
            return error_payload("scope must be one of: organization, anonymous.")

        client = get_singleton_client()
        result = await personal_assistant_provider().create_share_link(
            client,
            item_id=item_id,
            link_type=normalized_link_type,
            scope=normalized_scope,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def upload_small_text_file(
        file_name: str,
        content: str,
        parent_item_id: str | None = None,
        content_type: str = "text/plain",
    ) -> str:
        """Upload a small UTF-8 text file to OneDrive root or a specific folder item ID."""
        if not file_name.strip():
            return error_payload("file_name is required.")
        if not content.strip():
            return error_payload("content is required.")
        if parent_item_id is not None and not parent_item_id.strip():
            return error_payload("parent_item_id must be a non-empty string when provided.")
        if not content_type.strip():
            return error_payload("content_type is required.")

        client = get_singleton_client()
        result = await personal_assistant_provider().upload_small_text_file(
            client,
            file_name=file_name,
            content=content,
            parent_item_id=parent_item_id,
            content_type=content_type,
        )
        return json.dumps(result, indent=2, default=str)

    return {
        "get_contacts": get_contacts,
        "get_recent_files": get_recent_files,
        "search_files": search_files,
        "list_drive_items": list_drive_items,
        "create_share_link": create_share_link,
        "upload_small_text_file": upload_small_text_file,
    }
