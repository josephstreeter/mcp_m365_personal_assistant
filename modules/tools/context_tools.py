"""Context/intelligence/OneNote MCP wrappers."""

from __future__ import annotations

import json
from datetime import date
from typing import Any, Callable
from zoneinfo import ZoneInfo


def register_context_tools(
    *,
    mcp: Any,
    get_singleton_client: Callable[[], Any],
    personal_assistant_provider: Callable[[], Any],
    error_payload: Callable[..., str],
):
    @mcp.tool()
    async def get_relevant_people(top: int = 25) -> str:
        """Get people most relevant to the user."""
        if top < 1 or top > 200:
            return error_payload("top must be between 1 and 200.")

        client = get_singleton_client()
        results = await personal_assistant_provider().get_relevant_people(client, top=top)
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    async def get_trending_files(top: int = 25) -> str:
        """Get documents trending around the user."""
        if top < 1 or top > 200:
            return error_payload("top must be between 1 and 200.")

        client = get_singleton_client()
        results = await personal_assistant_provider().get_trending_files(client, top=top)
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    async def get_onenote_notebooks() -> str:
        """Get the user's OneNote notebooks and their sections."""
        client = get_singleton_client()
        results = await personal_assistant_provider().get_onenote_notebooks(client)
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    async def get_onenote_pages(section_id: str, top: int = 25) -> str:
        """Get pages from a specific OneNote section."""
        if not section_id.strip():
            return error_payload("section_id is required.")
        if top < 1 or top > 200:
            return error_payload("top must be between 1 and 200.")

        client = get_singleton_client()
        results = await personal_assistant_provider().get_onenote_pages(client, section_id=section_id, top=top)
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    async def get_onenote_page_content(page_id: str) -> str:
        """Get rendered HTML content and metadata for a OneNote page."""
        if not page_id.strip():
            return error_payload("page_id is required.")

        client = get_singleton_client()
        result = await personal_assistant_provider().get_onenote_page_content(client, page_id=page_id)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def create_onenote_page(section_id: str, title: str, content_html: str) -> str:
        """Create a OneNote page in the specified section."""
        if not section_id.strip():
            return error_payload("section_id is required.")
        if not title.strip():
            return error_payload("title is required.")
        if not content_html.strip():
            return error_payload("content_html is required.")

        client = get_singleton_client()
        result = await personal_assistant_provider().create_onenote_page(
            client,
            section_id=section_id,
            title=title,
            content_html=content_html,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def get_daily_briefing(date_value: str | None = None, timezone_name: str = "UTC") -> str:
        """Build a compact daily summary of calendar, mail, tasks, files, and people context."""
        if date_value is not None:
            try:
                date.fromisoformat(date_value)
            except ValueError:
                return error_payload("date_value must be in YYYY-MM-DD format.")

        try:
            ZoneInfo(timezone_name)
        except Exception:
            return error_payload("timezone_name must be a valid IANA timezone, for example 'UTC' or 'America/Chicago'.")

        client = get_singleton_client()
        result = await personal_assistant_provider().get_daily_briefing(
            client, date_value=date_value, timezone_name=timezone_name
        )
        if isinstance(result, dict):
            result.setdefault("version", 2)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def prepare_meeting_brief(event_id: str, include_recent_threads: bool = True) -> str:
        """Build a pre-meeting context bundle for an event, attendees, related mail, and files."""
        if not event_id.strip():
            return error_payload("event_id is required.")

        client = get_singleton_client()
        result = await personal_assistant_provider().prepare_meeting_brief(
            client,
            event_id=event_id,
            include_recent_threads=include_recent_threads,
        )
        if isinstance(result, dict):
            result.setdefault("version", 2)
        return json.dumps(result, indent=2, default=str)

    return {
        "get_relevant_people": get_relevant_people,
        "get_trending_files": get_trending_files,
        "get_onenote_notebooks": get_onenote_notebooks,
        "get_onenote_pages": get_onenote_pages,
        "get_onenote_page_content": get_onenote_page_content,
        "create_onenote_page": create_onenote_page,
        "get_daily_briefing": get_daily_briefing,
        "prepare_meeting_brief": prepare_meeting_brief,
    }
