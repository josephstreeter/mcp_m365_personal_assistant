"""To Do and profile MCP tool wrappers."""

from __future__ import annotations

import json
from typing import Any, Callable

from modules.enums import TodoStatus


def register_todo_tools(
    *,
    mcp: Any,
    get_singleton_client: Callable[[], Any],
    personal_assistant_provider: Callable[[], Any],
    error_payload: Callable[..., str],
    is_valid_iso8601_datetime: Callable[[str], bool],
):
    @mcp.tool()
    async def get_user_profile() -> str:
        """Get the current user's Microsoft 365 profile (name, email, job title).

        Example:
            >>> await get_user_profile()
        """
        client = get_singleton_client()
        result = await personal_assistant_provider().get_user_profile(client)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def get_todo_tasks() -> str:
        """Get all tasks from the user's Microsoft To Do lists.

        Example:
            >>> await get_todo_tasks()
        """
        client = get_singleton_client()
        results = await personal_assistant_provider().get_todo_tasks(client)
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    async def get_todo_lists() -> str:
        """List Microsoft To Do lists."""
        client = get_singleton_client()
        result = await personal_assistant_provider().get_todo_lists(client)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def create_todo_task(list_name: str, title: str, due_date: str | None = None) -> str:
        """Create a new task in a Microsoft To Do list."""
        if not list_name.strip():
            return error_payload("list_name is required.")
        if not title.strip():
            return error_payload("title is required.")
        if due_date is not None and not is_valid_iso8601_datetime(due_date):
            return error_payload("due_date must be an ISO 8601 datetime.")

        client = get_singleton_client()
        result = await personal_assistant_provider().create_todo_task(
            client, list_name=list_name, title=title, due_date=due_date
        )
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
            return error_payload("list_id is required.")
        if not task_id.strip():
            return error_payload("task_id is required.")
        if title is not None and not title.strip():
            return error_payload("title must be a non-empty string when provided.")
        if due_date is not None and not is_valid_iso8601_datetime(due_date):
            return error_payload("due_date must be an ISO 8601 datetime.")

        normalized_status = status
        allowed_statuses = {item.value for item in TodoStatus}
        if status is not None:
            if not status.strip():
                return error_payload("status must be a non-empty string when provided.")
            if status not in allowed_statuses:
                return error_payload(
                    "status must be one of: notStarted, inProgress, completed, waitingOnOthers, deferred."
                )
            normalized_status = status

        if title is None and due_date is None and normalized_status is None:
            return error_payload("At least one of title, due_date, or status must be provided.")

        client = get_singleton_client()
        result = await personal_assistant_provider().update_todo_task(
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
            return error_payload("list_id is required.")
        if not task_id.strip():
            return error_payload("task_id is required.")

        client = get_singleton_client()
        result = await personal_assistant_provider().delete_todo_task(client, list_id=list_id, task_id=task_id)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def create_todo_list(display_name: str) -> str:
        """Create a new Microsoft To Do list."""
        if not display_name.strip():
            return error_payload("display_name is required.")

        client = get_singleton_client()
        result = await personal_assistant_provider().create_todo_list(client, display_name=display_name)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def complete_todo_task(list_name: str, task_title: str) -> str:
        """Mark a task as completed in a Microsoft To Do list."""
        if not list_name.strip():
            return error_payload("list_name is required.")
        if not task_title.strip():
            return error_payload("task_title is required.")

        client = get_singleton_client()
        result = await personal_assistant_provider().complete_todo_task(
            client, list_name=list_name, task_title=task_title
        )
        return json.dumps(result, indent=2, default=str)

    return {
        "get_user_profile": get_user_profile,
        "get_todo_tasks": get_todo_tasks,
        "get_todo_lists": get_todo_lists,
        "create_todo_task": create_todo_task,
        "update_todo_task": update_todo_task,
        "delete_todo_task": delete_todo_task,
        "create_todo_list": create_todo_list,
        "complete_todo_task": complete_todo_task,
    }
