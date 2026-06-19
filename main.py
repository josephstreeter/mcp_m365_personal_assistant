"""
M365 Personal MCP Server
Provides MCP tools for Microsoft 365 personal productivity operations.
"""

import argparse
from datetime import date, datetime, timezone
import json
import logging
from zoneinfo import ZoneInfo

from fastmcp import FastMCP
from modules.graph_client import ALL_SCOPES, ConfigurationError, get_singleton_client, validate_environment
from modules import personal_assistant

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

mcp = FastMCP("m365-productivity-assistant-mcp")

RECOMMENDED_V2_SCOPES = [
    "Mail.ReadWrite",
    "Files.ReadWrite",
    "Notes.ReadWrite",
    "ChannelMessage.Send",
]

V2_TOOL_NAMES = {
    "reply_to_message",
    "forward_message",
    "mark_message_read",
    "list_mail_folders",
    "move_message",
    "get_message_attachments",
    "respond_to_event",
    "update_calendar_event",
    "find_meeting_times",
    "get_todo_lists",
    "update_todo_task",
    "delete_todo_task",
    "create_todo_list",
    "list_drive_items",
    "create_share_link",
    "upload_small_text_file",
    "get_chat_participants",
    "send_channel_message",
    "get_onenote_page_content",
    "create_onenote_page",
    "get_daily_briefing",
    "prepare_meeting_brief",
    "health_check",
    "list_supported_tools",
    "get_effective_scopes",
}

TOOL_SCOPE_MAP: dict[str, list[str]] = {
    "get_user_profile": ["User.Read"],
    "get_todo_tasks": ["Tasks.Read"],
    "get_todo_lists": ["Tasks.Read"],
    "create_todo_task": ["Tasks.ReadWrite"],
    "update_todo_task": ["Tasks.ReadWrite"],
    "delete_todo_task": ["Tasks.ReadWrite"],
    "create_todo_list": ["Tasks.ReadWrite"],
    "complete_todo_task": ["Tasks.ReadWrite"],
    "get_messages": ["Mail.Read"],
    "send_message": ["Mail.Send"],
    "search_messages": ["Mail.Read"],
    "get_message_by_id": ["Mail.Read"],
    "reply_to_message": ["Mail.ReadWrite", "Mail.Send"],
    "mark_message_read": ["Mail.ReadWrite"],
    "list_mail_folders": ["Mail.Read"],
    "move_message": ["Mail.ReadWrite"],
    "get_message_attachments": ["Mail.Read"],
    "get_calendar_events": ["Calendars.Read"],
    "create_calendar_event": ["Calendars.ReadWrite"],
    "update_calendar_event": ["Calendars.ReadWrite"],
    "delete_calendar_event": ["Calendars.ReadWrite"],
    "respond_to_event": ["Calendars.ReadWrite"],
    "find_meeting_times": ["Calendars.Read"],
    "get_contacts": ["Contacts.Read"],
    "get_recent_files": ["Files.Read"],
    "search_files": ["Files.Read"],
    "list_drive_items": ["Files.Read"],
    "create_share_link": ["Files.ReadWrite"],
    "upload_small_text_file": ["Files.ReadWrite"],
    "get_teams_chats": ["Chat.Read"],
    "get_chat_messages": ["Chat.Read"],
    "get_chat_participants": ["Chat.Read"],
    "send_chat_message": ["Chat.ReadWrite"],
    "send_channel_message": ["ChannelMessage.Send", "Group.Read.All"],
    "get_teams_and_channels": ["Channel.ReadBasic.All", "Group.Read.All"],
    "get_user_presence": ["Presence.Read.All"],
    "get_relevant_people": ["People.Read"],
    "get_trending_files": ["Files.Read.All"],
    "get_onenote_notebooks": ["Notes.Read"],
    "get_onenote_pages": ["Notes.Read"],
    "get_onenote_page_content": ["Notes.Read"],
    "create_onenote_page": ["Notes.ReadWrite"],
    "get_daily_briefing": ["User.Read", "Calendars.Read", "Mail.Read", "Tasks.Read", "Files.Read", "People.Read"],
    "prepare_meeting_brief": ["Calendars.Read", "Mail.Read", "Files.Read", "People.Read"],
    "health_check": ["User.Read"],
    "get_effective_scopes": [],
    "list_supported_tools": [],
}


def _error_payload(message: str, error_type: str = "ValidationError", retryable: bool = False) -> str:
    """Return a consistent JSON error payload for MCP wrapper validation failures."""
    return json.dumps(
        {
            "error": message,
            "error_type": error_type,
            "retryable": retryable,
        },
        indent=2,
        default=str,
    )


def _is_valid_iso8601_datetime(value: str) -> bool:
    """Validate ISO 8601 datetime strings, including Z suffix."""
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False

try:
    validate_environment()
    logger.info("Personal server initialized successfully")
except ConfigurationError as e:
    logger.error(f"Configuration error: {e}")
    raise


@mcp.tool()
async def get_user_profile() -> str:
    """Get the current user's Microsoft 365 profile (name, email, job title)."""
    client = get_singleton_client()
    result = await personal_assistant.get_user_profile(client)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def get_todo_tasks() -> str:
    """Get all tasks from the user's Microsoft To Do lists."""
    client = get_singleton_client()
    results = await personal_assistant.get_todo_tasks(client)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_todo_lists() -> str:
    """List Microsoft To Do lists."""
    client = get_singleton_client()
    result = await personal_assistant.get_todo_lists(client)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def create_todo_task(list_name: str, title: str, due_date: str | None = None) -> str:
    """Create a new task in a Microsoft To Do list.

    Args:
        list_name: Name of the To Do list to add the task to.
        title: Title of the new task.
        due_date: Optional due date in ISO 8601 format.
    """
    if not list_name.strip():
        return _error_payload("list_name is required.")
    if not title.strip():
        return _error_payload("title is required.")
    if due_date is not None and not _is_valid_iso8601_datetime(due_date):
        return _error_payload("due_date must be an ISO 8601 datetime.")

    client = get_singleton_client()
    result = await personal_assistant.create_todo_task(client, list_name=list_name, title=title, due_date=due_date)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def update_todo_task(
    list_id: str,
    task_id: str,
    title: str | None = None,
    due_date: str | None = None,
    status: str | None = None,
) -> str:
    """Update a Microsoft To Do task by list/task IDs."""
    if not list_id.strip():
        return _error_payload("list_id is required.")
    if not task_id.strip():
        return _error_payload("task_id is required.")
    if title is not None and not title.strip():
        return _error_payload("title must be a non-empty string when provided.")
    if due_date is not None and not _is_valid_iso8601_datetime(due_date):
        return _error_payload("due_date must be an ISO 8601 datetime.")

    normalized_status = status
    allowed_statuses = {"notStarted", "inProgress", "completed", "waitingOnOthers", "deferred"}
    if status is not None:
        if not status.strip():
            return _error_payload("status must be a non-empty string when provided.")
        if status not in allowed_statuses:
            return _error_payload(
                "status must be one of: notStarted, inProgress, completed, waitingOnOthers, deferred."
            )
        normalized_status = status

    if title is None and due_date is None and normalized_status is None:
        return _error_payload("At least one of title, due_date, or status must be provided.")

    client = get_singleton_client()
    result = await personal_assistant.update_todo_task(
        client,
        list_id=list_id,
        task_id=task_id,
        title=title,
        due_date=due_date,
        status=normalized_status,
    )
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def delete_todo_task(list_id: str, task_id: str) -> str:
    """Delete a Microsoft To Do task by list/task IDs."""
    if not list_id.strip():
        return _error_payload("list_id is required.")
    if not task_id.strip():
        return _error_payload("task_id is required.")

    client = get_singleton_client()
    result = await personal_assistant.delete_todo_task(client, list_id=list_id, task_id=task_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def create_todo_list(display_name: str) -> str:
    """Create a new Microsoft To Do list."""
    if not display_name.strip():
        return _error_payload("display_name is required.")

    client = get_singleton_client()
    result = await personal_assistant.create_todo_list(client, display_name=display_name)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def complete_todo_task(list_name: str, task_title: str) -> str:
    """Mark a task as completed in a Microsoft To Do list.

    Args:
        list_name: Name of the To Do list containing the task.
        task_title: Title of the task to mark as completed.
    """
    if not list_name.strip():
        return _error_payload("list_name is required.")
    if not task_title.strip():
        return _error_payload("task_title is required.")

    client = get_singleton_client()
    result = await personal_assistant.complete_todo_task(client, list_name=list_name, task_title=task_title)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def get_messages(top: int = 25, mailbox: str | None = None) -> str:
    """Get the user's most recent Exchange Online email messages."""
    if top < 1 or top > 200:
        return _error_payload("top must be between 1 and 200.")

    client = get_singleton_client()
    results = await personal_assistant.get_messages(client, top=top, mailbox=mailbox)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def send_message(to: str, subject: str, body: str, content_type: str = "text", from_address: str | None = None) -> str:
    """Send an email message."""
    if not to.strip():
        return _error_payload("to is required.")
    if not subject.strip():
        return _error_payload("subject is required.")
    if not body.strip():
        return _error_payload("body is required.")
    normalized_content_type = content_type.strip().lower()
    if normalized_content_type not in {"text", "html"}:
        return _error_payload("content_type must be one of: text, html.")

    client = get_singleton_client()
    result = await personal_assistant.send_message(
        client,
        to=to,
        subject=subject,
        body=body,
        content_type=normalized_content_type,
        from_address=from_address,
    )
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def search_messages(query: str, top: int = 25, mailbox: str | None = None) -> str:
    """Search the user's mailbox using a keyword query."""
    if not query.strip():
        return _error_payload("query is required.")
    if top < 1 or top > 200:
        return _error_payload("top must be between 1 and 200.")

    client = get_singleton_client()
    results = await personal_assistant.search_messages(client, query=query, top=top, mailbox=mailbox)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_message_by_id(message_id: str, mailbox: str | None = None) -> str:
    """Retrieve a single Exchange Online email message by its Graph API message ID."""
    if not message_id.strip():
        return _error_payload("message_id is required.")

    client = get_singleton_client()
    result = await personal_assistant.get_message_by_id(client, message_id=message_id, mailbox=mailbox)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def reply_to_message(
    message_id: str,
    body: str,
    content_type: str = "text",
    reply_all: bool = False,
    mailbox: str | None = None,
) -> str:
    """Reply to an existing Exchange Online email message."""
    if not message_id.strip():
        return _error_payload("message_id is required.")
    if not body.strip():
        return _error_payload("body is required.")
    normalized_content_type = content_type.strip().lower()
    if normalized_content_type not in {"text", "html"}:
        return _error_payload("content_type must be one of: text, html.")

    client = get_singleton_client()
    result = await personal_assistant.reply_to_message(
        client,
        message_id=message_id,
        body=body,
        content_type=normalized_content_type,
        reply_all=reply_all,
        mailbox=mailbox,
    )
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def forward_message(
    message_id: str,
    to: list[str],
    comment: str | None = None,
    mailbox: str | None = None,
) -> str:
    """Forward an Exchange Online email message to one or more recipients."""
    if not message_id.strip():
        return _error_payload("message_id is required.")
    if not to or not isinstance(to, list):
        return _error_payload("to must be a non-empty list of email addresses.")
    if len(to) == 0:
        return _error_payload("to must contain at least one email address.")
    if any(not email.strip() for email in to):
        return _error_payload("to must contain non-empty email addresses.")
    if comment is not None and not isinstance(comment, str):
        return _error_payload("comment must be a string when provided.")

    client = get_singleton_client()
    result = await personal_assistant.forward_message(
        client,
        message_id=message_id,
        to=to,
        comment=comment,
        mailbox=mailbox,
    )
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def mark_message_read(message_id: str, is_read: bool = True, mailbox: str | None = None) -> str:
    """Mark an Exchange Online email message as read or unread."""
    if not message_id.strip():
        return _error_payload("message_id is required.")

    client = get_singleton_client()
    result = await personal_assistant.mark_message_read(client, message_id=message_id, is_read=is_read, mailbox=mailbox)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def list_mail_folders(top: int = 100, mailbox: str | None = None) -> str:
    """List mail folders and their IDs for the current or shared mailbox."""
    if top < 1 or top > 200:
        return _error_payload("top must be between 1 and 200.")

    client = get_singleton_client()
    results = await personal_assistant.list_mail_folders(client, top=top, mailbox=mailbox)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def move_message(message_id: str, destination_folder_id: str, mailbox: str | None = None) -> str:
    """Move an Exchange Online email message to a destination folder."""
    if not message_id.strip():
        return _error_payload("message_id is required.")
    if not destination_folder_id.strip():
        return _error_payload("destination_folder_id is required.")

    client = get_singleton_client()
    result = await personal_assistant.move_message(
        client,
        message_id=message_id,
        destination_folder_id=destination_folder_id,
        mailbox=mailbox,
    )
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def get_message_attachments(message_id: str, mailbox: str | None = None) -> str:
    """Get attachment metadata for an Exchange Online email message."""
    if not message_id.strip():
        return _error_payload("message_id is required.")

    client = get_singleton_client()
    result = await personal_assistant.get_message_attachments(client, message_id=message_id, mailbox=mailbox)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def get_calendar_events(days: int = 7) -> str:
    """Get the user's calendar events for the next N days."""
    client = get_singleton_client()
    results = await personal_assistant.get_calendar_events(client, days=days)
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
    result = await personal_assistant.create_calendar_event(
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
        return _error_payload("event_id is required.")
    if start is not None and not _is_valid_iso8601_datetime(start):
        return _error_payload("start must be an ISO 8601 datetime.")
    if end is not None and not _is_valid_iso8601_datetime(end):
        return _error_payload("end must be an ISO 8601 datetime.")
    if attendees is not None and any(not attendee.strip() for attendee in attendees):
        return _error_payload("attendees must contain non-empty email addresses.")

    client = get_singleton_client()
    result = await personal_assistant.update_calendar_event(
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
        return _error_payload("event_id is required.")

    client = get_singleton_client()
    result = await personal_assistant.delete_calendar_event(client, event_id=event_id)
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
        return _error_payload("event_id is required.")

    normalized = response.strip().lower()
    if normalized not in {"accept", "decline", "tentative"}:
        return _error_payload("response must be one of: accept, decline, tentative.")

    client = get_singleton_client()
    result = await personal_assistant.respond_to_event(
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
        return _error_payload("attendees must include at least one email address.")
    if any(not attendee.strip() for attendee in attendees):
        return _error_payload("attendees must contain non-empty email addresses.")
    if duration_minutes <= 0:
        return _error_payload("duration_minutes must be greater than 0.")
    if max_candidates < 1 or max_candidates > 50:
        return _error_payload("max_candidates must be between 1 and 50.")
    if not _is_valid_iso8601_datetime(time_window_start):
        return _error_payload("time_window_start must be an ISO 8601 datetime.")
    if not _is_valid_iso8601_datetime(time_window_end):
        return _error_payload("time_window_end must be an ISO 8601 datetime.")

    client = get_singleton_client()
    result = await personal_assistant.find_meeting_times(
        client,
        attendees=attendees,
        duration_minutes=duration_minutes,
        time_window_start=time_window_start,
        time_window_end=time_window_end,
        max_candidates=max_candidates,
    )
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def get_contacts(top: int = 25) -> str:
    """Get the user's contacts from their address book."""
    if top < 1 or top > 200:
        return _error_payload("top must be between 1 and 200.")

    client = get_singleton_client()
    results = await personal_assistant.get_contacts(client, top=top)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_recent_files(top: int = 25) -> str:
    """Get the user's recently accessed OneDrive files."""
    if top < 1 or top > 200:
        return _error_payload("top must be between 1 and 200.")

    client = get_singleton_client()
    results = await personal_assistant.get_recent_files(client, top=top)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def search_files(query: str, top: int = 25) -> str:
    """Search for files in OneDrive and SharePoint by keyword."""
    if not query.strip():
        return _error_payload("query is required.")
    if top < 1 or top > 200:
        return _error_payload("top must be between 1 and 200.")

    client = get_singleton_client()
    results = await personal_assistant.search_files(client, query=query, top=top)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def list_drive_items(item_id: str | None = None, top: int = 50) -> str:
    """List OneDrive folder contents for root or a specific folder item ID."""
    if item_id is not None and not item_id.strip():
        return _error_payload("item_id must be a non-empty string when provided.")
    if top < 1 or top > 200:
        return _error_payload("top must be between 1 and 200.")

    client = get_singleton_client()
    result = await personal_assistant.list_drive_items(client, item_id=item_id, top=top)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def create_share_link(item_id: str, link_type: str = "view", scope: str = "organization") -> str:
    """Create a share link for a OneDrive item."""
    if not item_id.strip():
        return _error_payload("item_id is required.")

    normalized_link_type = link_type.strip().lower()
    if normalized_link_type not in {"view", "edit"}:
        return _error_payload("link_type must be one of: view, edit.")

    normalized_scope = scope.strip().lower()
    if normalized_scope not in {"organization", "anonymous"}:
        return _error_payload("scope must be one of: organization, anonymous.")

    client = get_singleton_client()
    result = await personal_assistant.create_share_link(
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
        return _error_payload("file_name is required.")
    if not content.strip():
        return _error_payload("content is required.")
    if parent_item_id is not None and not parent_item_id.strip():
        return _error_payload("parent_item_id must be a non-empty string when provided.")
    if not content_type.strip():
        return _error_payload("content_type is required.")

    client = get_singleton_client()
    result = await personal_assistant.upload_small_text_file(
        client,
        file_name=file_name,
        content=content,
        parent_item_id=parent_item_id,
        content_type=content_type,
    )
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def get_teams_chats(top: int = 25) -> str:
    """Get the user's recent Teams chat threads."""
    if top < 1 or top > 200:
        return _error_payload("top must be between 1 and 200.")

    client = get_singleton_client()
    results = await personal_assistant.get_teams_chats(client, top=top)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_chat_messages(chat_id: str, top: int = 25) -> str:
    """Get messages from a specific Teams chat."""
    if not chat_id.strip():
        return _error_payload("chat_id is required.")
    if top < 1 or top > 200:
        return _error_payload("top must be between 1 and 200.")

    client = get_singleton_client()
    results = await personal_assistant.get_chat_messages(client, chat_id=chat_id, top=top)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_chat_participants(chat_id: str) -> str:
    """Get participant identities for a specific Teams chat."""
    if not chat_id.strip():
        return _error_payload("chat_id is required.")

    client = get_singleton_client()
    result = await personal_assistant.get_chat_participants(client, chat_id=chat_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def send_chat_message(message: str, recipient: str | None = None, chat_id: str | None = None, content_type: str = "text") -> str:
    """Send a Teams chat message to a user or existing chat."""
    if not message.strip():
        return _error_payload("message is required.")
    if not recipient and not chat_id:
        return _error_payload("Either recipient or chat_id is required.")
    if recipient is not None and not recipient.strip():
        return _error_payload("recipient must be a non-empty string when provided.")
    if chat_id is not None and not chat_id.strip():
        return _error_payload("chat_id must be a non-empty string when provided.")
    normalized_content_type = content_type.strip().lower()
    if normalized_content_type not in {"text", "html"}:
        return _error_payload("content_type must be one of: text, html.")

    client = get_singleton_client()
    result = await personal_assistant.send_chat_message(
        client,
        message=message,
        recipient=recipient,
        chat_id=chat_id,
        content_type=normalized_content_type,
    )
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def send_channel_message(team_id: str, channel_id: str, message: str, content_type: str = "text") -> str:
    """Send a message to a Microsoft Teams channel."""
    if not team_id.strip():
        return _error_payload("team_id is required.")
    if not channel_id.strip():
        return _error_payload("channel_id is required.")
    if not message.strip():
        return _error_payload("message is required.")
    normalized_content_type = content_type.strip().lower()
    if normalized_content_type not in {"text", "html"}:
        return _error_payload("content_type must be one of: text, html.")

    client = get_singleton_client()
    result = await personal_assistant.send_channel_message(
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
    results = await personal_assistant.get_teams_and_channels(client)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_user_presence(user_ids: list[str] | None = None) -> str:
    """Get the presence status for the current user or specified users."""
    if user_ids is not None:
        if not user_ids:
            return _error_payload("user_ids must include at least one user id when provided.")
        if any(not user_id.strip() for user_id in user_ids):
            return _error_payload("user_ids must contain non-empty values.")

    client = get_singleton_client()
    results = await personal_assistant.get_user_presence(client, user_ids=user_ids)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_relevant_people(top: int = 25) -> str:
    """Get people most relevant to the user."""
    if top < 1 or top > 200:
        return _error_payload("top must be between 1 and 200.")

    client = get_singleton_client()
    results = await personal_assistant.get_relevant_people(client, top=top)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_trending_files(top: int = 25) -> str:
    """Get documents trending around the user."""
    if top < 1 or top > 200:
        return _error_payload("top must be between 1 and 200.")

    client = get_singleton_client()
    results = await personal_assistant.get_trending_files(client, top=top)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_onenote_notebooks() -> str:
    """Get the user's OneNote notebooks and their sections."""
    client = get_singleton_client()
    results = await personal_assistant.get_onenote_notebooks(client)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_onenote_pages(section_id: str, top: int = 25) -> str:
    """Get pages from a specific OneNote section."""
    if not section_id.strip():
        return _error_payload("section_id is required.")
    if top < 1 or top > 200:
        return _error_payload("top must be between 1 and 200.")

    client = get_singleton_client()
    results = await personal_assistant.get_onenote_pages(client, section_id=section_id, top=top)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_onenote_page_content(page_id: str) -> str:
    """Get rendered HTML content and metadata for a OneNote page."""
    if not page_id.strip():
        return _error_payload("page_id is required.")

    client = get_singleton_client()
    result = await personal_assistant.get_onenote_page_content(client, page_id=page_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def create_onenote_page(section_id: str, title: str, content_html: str) -> str:
    """Create a OneNote page in the specified section."""
    if not section_id.strip():
        return _error_payload("section_id is required.")
    if not title.strip():
        return _error_payload("title is required.")
    if not content_html.strip():
        return _error_payload("content_html is required.")

    client = get_singleton_client()
    result = await personal_assistant.create_onenote_page(
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
            return _error_payload("date_value must be in YYYY-MM-DD format.")

    try:
        ZoneInfo(timezone_name)
    except Exception:
        return _error_payload("timezone_name must be a valid IANA timezone, for example 'UTC' or 'America/Chicago'.")

    client = get_singleton_client()
    result = await personal_assistant.get_daily_briefing(client, date_value=date_value, timezone_name=timezone_name)
    if isinstance(result, dict):
        result.setdefault("version", 2)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def prepare_meeting_brief(event_id: str, include_recent_threads: bool = True) -> str:
    """Build a pre-meeting context bundle for an event, attendees, related mail, and files."""
    if not event_id.strip():
        return _error_payload("event_id is required.")

    client = get_singleton_client()
    result = await personal_assistant.prepare_meeting_brief(
        client,
        event_id=event_id,
        include_recent_threads=include_recent_threads,
    )
    if isinstance(result, dict):
        result.setdefault("version", 2)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def health_check() -> str:
    """Verify authentication and Graph connectivity."""
    client = get_singleton_client()
    result = await personal_assistant.health_check(client)
    if isinstance(result, dict):
        result.setdefault("version", 2)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def get_effective_scopes() -> str:
    """Return configured scopes and inferred missing recommended scopes."""
    configured_scopes = sorted(ALL_SCOPES)
    missing_recommended = [scope for scope in RECOMMENDED_V2_SCOPES if scope not in configured_scopes]

    result = {
        "configured_scopes": configured_scopes,
        "granted_scopes": None,
        "missing_recommended_scopes": missing_recommended,
        "version": 2,
    }
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def list_supported_tools() -> str:
    """List supported MCP tools with scope mapping."""
    tools = []
    for tool_name, required_scopes in sorted(TOOL_SCOPE_MAP.items()):
        tool_fn = globals().get(tool_name)
        if not callable(tool_fn):
            continue
        doc = (tool_fn.__doc__ or "").strip().splitlines()
        description = doc[0] if doc else ""
        tools.append(
            {
                "name": tool_name,
                "description": description,
                "required_scopes": required_scopes,
                "version": "2" if tool_name in V2_TOOL_NAMES else "1",
            }
        )

    result = {
        "tools": tools,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "version": 2,
    }
    return json.dumps(result, indent=2, default=str)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="M365 Personal MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode: stdio (default) or http",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to for HTTP transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to for HTTP transport (default: 8000)",
    )

    args = parser.parse_args()

    if args.transport == "http":
        logger.info(f"Starting personal MCP server in HTTP mode on {args.host}:{args.port}")
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        logger.info("Starting personal MCP server in stdio mode")
        mcp.run()
