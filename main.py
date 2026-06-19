"""
M365 Personal MCP Server
Provides MCP tools for Microsoft 365 personal productivity operations.
"""

import argparse
from datetime import datetime
import json
import logging

from fastmcp import FastMCP

from modules.graph_client import ALL_SCOPES, ConfigurationError, get_singleton_client, validate_environment
from modules import personal_assistant
from modules.logging_utils import configure_structured_logging
from modules.tools.calendar_tools import register_calendar_tools
from modules.tools.context_tools import register_context_tools
from modules.tools.files_tools import register_files_tools
from modules.tools.mail_tools import register_mail_tools
from modules.tools.operability_tools import register_operability_tools
from modules.tools.teams_tools import register_teams_tools
from modules.tools.todo_tools import register_todo_tools

configure_structured_logging(level=logging.INFO)
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


_domain_exports: dict[str, object] = {}
_domain_exports.update(
    register_todo_tools(
        mcp=mcp,
        get_singleton_client=get_singleton_client,
        personal_assistant_provider=lambda: personal_assistant,
        error_payload=_error_payload,
        is_valid_iso8601_datetime=_is_valid_iso8601_datetime,
    )
)
_domain_exports.update(
    register_mail_tools(
        mcp=mcp,
        get_singleton_client=get_singleton_client,
        personal_assistant_provider=lambda: personal_assistant,
        error_payload=_error_payload,
    )
)
_domain_exports.update(
    register_calendar_tools(
        mcp=mcp,
        get_singleton_client=get_singleton_client,
        personal_assistant_provider=lambda: personal_assistant,
        error_payload=_error_payload,
        is_valid_iso8601_datetime=_is_valid_iso8601_datetime,
    )
)
_domain_exports.update(
    register_files_tools(
        mcp=mcp,
        get_singleton_client=get_singleton_client,
        personal_assistant_provider=lambda: personal_assistant,
        error_payload=_error_payload,
    )
)
_domain_exports.update(
    register_teams_tools(
        mcp=mcp,
        get_singleton_client=get_singleton_client,
        personal_assistant_provider=lambda: personal_assistant,
        error_payload=_error_payload,
    )
)
_domain_exports.update(
    register_context_tools(
        mcp=mcp,
        get_singleton_client=get_singleton_client,
        personal_assistant_provider=lambda: personal_assistant,
        error_payload=_error_payload,
    )
)

globals().update(_domain_exports)

_operability_exports = register_operability_tools(
    mcp=mcp,
    get_singleton_client=get_singleton_client,
    personal_assistant_provider=lambda: personal_assistant,
    all_scopes=ALL_SCOPES,
    recommended_v2_scopes=RECOMMENDED_V2_SCOPES,
    tool_scope_map=TOOL_SCOPE_MAP,
    v2_tool_names=V2_TOOL_NAMES,
    resolve_tool_fn=lambda name: globals().get(name),
)

globals().update(_operability_exports)


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
