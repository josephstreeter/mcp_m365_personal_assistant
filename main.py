"""
M365 Personal MCP Server
Provides MCP tools for Microsoft 365 personal productivity operations.
"""

import argparse
import json
import logging

from fastmcp import FastMCP
from modules.graph_client import ConfigurationError, get_singleton_client, validate_environment
from modules import personal_assistant

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

mcp = FastMCP("m365-productivity-assistant-mcp")

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
async def create_todo_task(list_name: str, title: str, due_date: str | None = None) -> str:
    """Create a new task in a Microsoft To Do list.

    Args:
        list_name: Name of the To Do list to add the task to.
        title: Title of the new task.
        due_date: Optional due date in ISO 8601 format.
    """
    client = get_singleton_client()
    result = await personal_assistant.create_todo_task(client, list_name=list_name, title=title, due_date=due_date)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def complete_todo_task(list_name: str, task_title: str) -> str:
    """Mark a task as completed in a Microsoft To Do list.

    Args:
        list_name: Name of the To Do list containing the task.
        task_title: Title of the task to mark as completed.
    """
    client = get_singleton_client()
    result = await personal_assistant.complete_todo_task(client, list_name=list_name, task_title=task_title)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def get_messages(top: int = 25, mailbox: str | None = None) -> str:
    """Get the user's most recent Exchange Online email messages."""
    client = get_singleton_client()
    results = await personal_assistant.get_messages(client, top=top, mailbox=mailbox)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def send_message(to: str, subject: str, body: str, content_type: str = "text", from_address: str | None = None) -> str:
    """Send an email message."""
    client = get_singleton_client()
    result = await personal_assistant.send_message(
        client,
        to=to,
        subject=subject,
        body=body,
        content_type=content_type,
        from_address=from_address,
    )
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def search_messages(query: str, top: int = 25, mailbox: str | None = None) -> str:
    """Search the user's mailbox using a keyword query."""
    client = get_singleton_client()
    results = await personal_assistant.search_messages(client, query=query, top=top, mailbox=mailbox)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_message_by_id(message_id: str, mailbox: str | None = None) -> str:
    """Retrieve a single Exchange Online email message by its Graph API message ID."""
    client = get_singleton_client()
    result = await personal_assistant.get_message_by_id(client, message_id=message_id, mailbox=mailbox)
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
async def get_contacts(top: int = 25) -> str:
    """Get the user's contacts from their address book."""
    client = get_singleton_client()
    results = await personal_assistant.get_contacts(client, top=top)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_recent_files(top: int = 25) -> str:
    """Get the user's recently accessed OneDrive files."""
    client = get_singleton_client()
    results = await personal_assistant.get_recent_files(client, top=top)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def search_files(query: str, top: int = 25) -> str:
    """Search for files in OneDrive and SharePoint by keyword."""
    client = get_singleton_client()
    results = await personal_assistant.search_files(client, query=query, top=top)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_teams_chats(top: int = 25) -> str:
    """Get the user's recent Teams chat threads."""
    client = get_singleton_client()
    results = await personal_assistant.get_teams_chats(client, top=top)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_chat_messages(chat_id: str, top: int = 25) -> str:
    """Get messages from a specific Teams chat."""
    client = get_singleton_client()
    results = await personal_assistant.get_chat_messages(client, chat_id=chat_id, top=top)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def send_chat_message(message: str, recipient: str | None = None, chat_id: str | None = None, content_type: str = "text") -> str:
    """Send a Teams chat message to a user or existing chat."""
    client = get_singleton_client()
    result = await personal_assistant.send_chat_message(
        client,
        message=message,
        recipient=recipient,
        chat_id=chat_id,
        content_type=content_type,
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
    client = get_singleton_client()
    results = await personal_assistant.get_user_presence(client, user_ids=user_ids)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_relevant_people(top: int = 25) -> str:
    """Get people most relevant to the user."""
    client = get_singleton_client()
    results = await personal_assistant.get_relevant_people(client, top=top)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def get_trending_files(top: int = 25) -> str:
    """Get documents trending around the user."""
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
    client = get_singleton_client()
    results = await personal_assistant.get_onenote_pages(client, section_id=section_id, top=top)
    return json.dumps(results, indent=2, default=str)


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
