"""Calendar MCP tool wrappers."""

from __future__ import annotations

import json
from typing import Any, Callable

from modules.enums import EventResponse


def register_calendar_tools(
    *,
    mcp: Any,
    get_singleton_client: Callable[[], Any],
    personal_assistant_provider: Callable[[], Any],
    error_payload: Callable[..., str],
    is_valid_iso8601_datetime: Callable[[str], bool],
):
    @mcp.tool()
    async def get_calendar_events(days: int = 7) -> str:
        """Get the user's calendar events for the next N days.

        Example:
            >>> await get_calendar_events(days=3)
        """
        client = get_singleton_client()
        results = await personal_assistant_provider().get_calendar_events(client, days=days)
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    async def create_calendar_event(
        subject: str,
        start: str,
        end: str,
        attendees: list[str] | None = None,
        location: str | None = None,
        body: str | None = None,
        is_all_day: bool = False,
    ) -> str:
        """Create a new calendar event."""
        client = get_singleton_client()
        result = await personal_assistant_provider().create_calendar_event(
            client,
            subject=subject,
            start=start,
            end=end,
            attendees=attendees,
            location=location,
            body=body,
            is_all_day=is_all_day,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def update_calendar_event(
        event_id: str,
        subject: str | None = None,
        start: str | None = None,
        end: str | None = None,
        attendees: list[str] | None = None,
        location: str | None = None,
        body: str | None = None,
        is_all_day: bool | None = None,
    ) -> str:
        """Update an existing calendar event."""
        if not event_id.strip():
            return error_payload("event_id is required.")
        if start is not None and not is_valid_iso8601_datetime(start):
            return error_payload("start must be an ISO 8601 datetime.")
        if end is not None and not is_valid_iso8601_datetime(end):
            return error_payload("end must be an ISO 8601 datetime.")
        if attendees is not None and any(not attendee.strip() for attendee in attendees):
            return error_payload("attendees must contain non-empty email addresses.")

        client = get_singleton_client()
        result = await personal_assistant_provider().update_calendar_event(
            client,
            event_id=event_id,
            subject=subject,
            start=start,
            end=end,
            attendees=attendees,
            location=location,
            body=body,
            is_all_day=is_all_day,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def delete_calendar_event(event_id: str) -> str:
        """Delete a calendar event by event ID."""
        if not event_id.strip():
            return error_payload("event_id is required.")

        client = get_singleton_client()
        result = await personal_assistant_provider().delete_calendar_event(client, event_id=event_id)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def respond_to_event(
        event_id: str,
        response: str,
        comment: str | None = None,
        send_response: bool = True,
    ) -> str:
        """Respond to a meeting invite (accept, decline, tentative)."""
        if not event_id.strip():
            return error_payload("event_id is required.")

        normalized = response.strip().lower()
        if normalized not in {item.value for item in EventResponse}:
            return error_payload("response must be one of: accept, decline, tentative.")

        client = get_singleton_client()
        result = await personal_assistant_provider().respond_to_event(
            client,
            event_id=event_id,
            response=normalized,
            comment=comment,
            send_response=send_response,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def find_meeting_times(
        attendees: list[str],
        duration_minutes: int,
        time_window_start: str,
        time_window_end: str,
        max_candidates: int = 10,
    ) -> str:
        """Find candidate meeting times from attendee schedules."""
        if not attendees:
            return error_payload("attendees must include at least one email address.")
        if any(not attendee.strip() for attendee in attendees):
            return error_payload("attendees must contain non-empty email addresses.")
        if duration_minutes <= 0:
            return error_payload("duration_minutes must be greater than 0.")
        if max_candidates < 1 or max_candidates > 50:
            return error_payload("max_candidates must be between 1 and 50.")
        if not is_valid_iso8601_datetime(time_window_start):
            return error_payload("time_window_start must be an ISO 8601 datetime.")
        if not is_valid_iso8601_datetime(time_window_end):
            return error_payload("time_window_end must be an ISO 8601 datetime.")

        client = get_singleton_client()
        result = await personal_assistant_provider().find_meeting_times(
            client,
            attendees=attendees,
            duration_minutes=duration_minutes,
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            max_candidates=max_candidates,
        )
        return json.dumps(result, indent=2, default=str)

    return {
        "get_calendar_events": get_calendar_events,
        "create_calendar_event": create_calendar_event,
        "update_calendar_event": update_calendar_event,
        "delete_calendar_event": delete_calendar_event,
        "respond_to_event": respond_to_event,
        "find_meeting_times": find_meeting_times,
    }
