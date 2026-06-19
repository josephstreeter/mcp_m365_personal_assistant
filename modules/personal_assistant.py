"""
Personal productivity functions for Microsoft 365 (M365) integration.
Handles user profile, email, calendar, tasks, contacts, files, Teams, and insights.
"""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo
from kiota_abstractions.base_request_configuration import RequestConfiguration
from modules.errors import (
    M365Exception,
    GraphAPIError,
    ValidationError,
    AuthenticationError,
    TimeoutError as M365TimeoutError,
    error_from_graph_exception,
)
from modules.cache import TTLCache
from modules.enums import ContentType, TodoStatus, EventResponse
from modules.logging_utils import log_event
from msgraph.graph_service_client import GraphServiceClient
from msgraph.generated.models.todo_task import TodoTask
from msgraph.generated.models.todo_task_list import TodoTaskList
from msgraph.generated.models.task_status import TaskStatus
from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone
from msgraph.generated.models.message import Message
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.users.item.messages.item.forward.forward_post_request_body import ForwardPostRequestBody
from msgraph.generated.users.item.messages.item.reply.reply_post_request_body import ReplyPostRequestBody
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.models.event import Event
from msgraph.generated.models.location import Location
from msgraph.generated.models.attendee import Attendee
from msgraph.generated.models.attendee_type import AttendeeType
from msgraph.generated.models.chat import Chat
from msgraph.generated.models.chat_type import ChatType
from msgraph.generated.models.chat_message import ChatMessage
from msgraph.generated.models.aad_user_conversation_member import AadUserConversationMember
from msgraph.generated.models.conversation_member import ConversationMember
from msgraph.generated.models.drive_item import DriveItem
from msgraph.generated.models.file import File
from msgraph.generated.models.onenote_page import OnenotePage
from msgraph.generated.users.item.messages.messages_request_builder import MessagesRequestBuilder
from msgraph.generated.users.item.messages.item.message_item_request_builder import MessageItemRequestBuilder
from msgraph.generated.users.item.mail_folders.mail_folders_request_builder import MailFoldersRequestBuilder
from msgraph.generated.users.item.messages.item.attachments.attachments_request_builder import AttachmentsRequestBuilder
from msgraph.generated.users.item.messages.item.reply.reply_post_request_body import ReplyPostRequestBody
from msgraph.generated.users.item.messages.item.reply_all.reply_all_post_request_body import ReplyAllPostRequestBody
from msgraph.generated.users.item.messages.item.move.move_post_request_body import MovePostRequestBody
from msgraph.generated.users.item.calendar_view.calendar_view_request_builder import CalendarViewRequestBuilder
from msgraph.generated.users.item.events.item.accept.accept_post_request_body import AcceptPostRequestBody
from msgraph.generated.users.item.events.item.decline.decline_post_request_body import DeclinePostRequestBody
from msgraph.generated.users.item.events.item.tentatively_accept.tentatively_accept_post_request_body import TentativelyAcceptPostRequestBody
from msgraph.generated.users.item.calendar.get_schedule.get_schedule_post_request_body import GetSchedulePostRequestBody
from msgraph.generated.users.item.contacts.contacts_request_builder import ContactsRequestBuilder
from msgraph.generated.users.item.chats.chats_request_builder import ChatsRequestBuilder
from msgraph.generated.users.item.chats.item.messages.messages_request_builder import MessagesRequestBuilder as ChatMessagesRequestBuilder
from msgraph.generated.users.item.people.people_request_builder import PeopleRequestBuilder
from msgraph.generated.users.item.onenote.sections.item.pages.pages_request_builder import PagesRequestBuilder
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import SendMailPostRequestBody
from msgraph.generated.communications.get_presences_by_user_id.get_presences_by_user_id_post_request_body import GetPresencesByUserIdPostRequestBody
from msgraph.generated.drives.item.items.item.children.children_request_builder import ChildrenRequestBuilder
from msgraph.generated.drives.item.items.item.create_link.create_link_post_request_body import CreateLinkPostRequestBody

logger = logging.getLogger(__name__)

GRAPH_CALL_TIMEOUT_SECONDS = 30
READ_CACHE_TTL_SECONDS = 300
_read_cache = TTLCache(default_ttl_seconds=READ_CACHE_TTL_SECONDS)


async def _graph_call(awaitable, operation: str):
    """Run a Graph SDK awaitable with a consistent timeout."""
    try:
        log_event(logger, logging.DEBUG, "graph_call_start", f"Starting Graph call: {operation}", operation=operation)
        result = await asyncio.wait_for(awaitable, timeout=GRAPH_CALL_TIMEOUT_SECONDS)
        log_event(logger, logging.DEBUG, "graph_call_success", f"Completed Graph call: {operation}", operation=operation)
        return result
    except asyncio.TimeoutError as exc:
        log_event(
            logger,
            logging.WARNING,
            "graph_call_timeout",
            f"Graph call timed out: {operation}",
            operation=operation,
            timeout_seconds=GRAPH_CALL_TIMEOUT_SECONDS,
        )
        raise M365TimeoutError(
            f"{operation} timed out after {GRAPH_CALL_TIMEOUT_SECONDS} seconds"
        ) from exc


def _cache_get(key: str):
    value = _read_cache.get(key)
    if value is None:
        log_event(logger, logging.DEBUG, "cache_miss", "Cache miss", key=key)
    else:
        log_event(logger, logging.DEBUG, "cache_hit", "Cache hit", key=key)
    return value


def _cache_set(key: str, value):
    log_event(logger, logging.DEBUG, "cache_set", "Cache set", key=key, ttl_seconds=READ_CACHE_TTL_SECONDS)
    return _read_cache.set(key, value)


def _cache_invalidate(prefix: str):
    log_event(logger, logging.DEBUG, "cache_invalidate", "Cache invalidation by prefix", prefix=prefix)
    _read_cache.invalidate_prefix(prefix)


# User Profile

async def get_user_profile(client: GraphServiceClient) -> dict:
    """
    Get the current user's profile.
    
    Args:
        client: Authenticated Graph API client
        
    Returns:
        dict: User profile information or error message
    """
    try:
        cache_key = "read:user_profile"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        profile = await _graph_call(client.me.get(), "Get user profile")
        if profile:
            result = {
                "display_name": profile.display_name,
                "email": profile.mail,
                "job_title": profile.job_title,
                "id": profile.id,
            }
            return _cache_set(cache_key, result)
        return {"error": "Could not retrieve user profile."}
    except asyncio.TimeoutError:
        exc = M365TimeoutError("User profile request timed out after 30 seconds")
        logger.warning(f"Graph API timeout: {exc.message}")
        return exc.to_dict()
    except Exception as e:
        exc = error_from_graph_exception(e)
        logger.error(f"Failed to get user profile: {exc.message}")
        return exc.to_dict()


# Microsoft To Do

async def get_todo_tasks(client: GraphServiceClient) -> list[dict]:
    """
    Get all tasks from the user's Microsoft To Do lists.
    
    Args:
        client: Authenticated Graph API client
        
    Returns:
        list[dict]: List of tasks or empty list on error
    """
    try:
        results = []
        task_lists = await _graph_call(client.me.todo.lists.get(), "Graph API call")
        if task_lists and task_lists.value:
            for task_list in task_lists.value:
                list_name = task_list.display_name
                if not task_list.id:
                    continue
                tasks = await _graph_call(client.me.todo.lists.by_todo_task_list_id(task_list.id).tasks.get(), "Graph API call")
                if tasks and tasks.value:
                    for task in tasks.value:
                        results.append({
                            "list": list_name,
                            "title": task.title,
                            "status": task.status.value if task.status else "unknown",
                            "due": task.due_date_time.date_time if task.due_date_time else None,
                        })
        return results
    except Exception as e:
        logger.error(f"Failed to get todo tasks: {e}")
        return [{"error": f"Failed to get todo tasks: {str(e)}"}]


async def get_todo_lists(client: GraphServiceClient) -> dict:
    """
    List Microsoft To Do lists.

    Args:
        client: Authenticated Graph API client

    Returns:
        dict: To Do lists payload or error
    """
    try:
        cache_key = "read:todo_lists"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        task_lists = await _graph_call(client.me.todo.lists.get(), "Graph API call")
        lists = []
        if task_lists and task_lists.value:
            for task_list in task_lists.value:
                lists.append(
                    {
                        "id": task_list.id,
                        "display_name": task_list.display_name,
                        "is_shared": task_list.is_shared,
                        "wellknown_list_name": task_list.wellknown_list_name.value if task_list.wellknown_list_name else None,
                    }
                )

        return _cache_set(cache_key, {"lists": lists})
    except Exception as e:
        log_event(
            logger,
            logging.ERROR,
            "todo_lists_fetch_failed",
            "Failed to get todo lists",
            error=str(e),
        )
        return {"error": f"Failed to get todo lists: {str(e)}"}


async def create_todo_task(client: GraphServiceClient, list_name: str, title: str, due_date: Optional[str] = None) -> dict:
    """
    Create a new task in a Microsoft To Do list.
    
    Args:
        client: Authenticated Graph API client
        list_name: Name of the To Do list
        title: Task title
        due_date: Optional due date in ISO 8601 format
        
    Returns:
        dict: Created task information or error message
    """
    try:
        task_lists = await _graph_call(client.me.todo.lists.get(), "Graph API call")
        target_list = None
        if task_lists and task_lists.value:
            for tl in task_lists.value:
                if tl.display_name and tl.display_name.lower() == list_name.lower():
                    target_list = tl
                    break
        
        if not target_list or not target_list.id:
            return {"error": f"Task list '{list_name}' not found."}

        new_task = TodoTask()
        new_task.title = title
        if due_date:
            due = DateTimeTimeZone()
            due.date_time = due_date
            due.time_zone = "UTC"
            new_task.due_date_time = due

        created = await _graph_call(client.me.todo.lists.by_todo_task_list_id(target_list.id).tasks.post(new_task), "Graph API call")
        if created:
            _cache_invalidate("read:todo")
            return {
                "id": created.id,
                "title": created.title,
                "status": created.status.value if created.status else "unknown",
            }
        return {"error": "Failed to create task."}
    except Exception as e:
        logger.error(f"Failed to create todo task: {e}")
        return {"error": f"Failed to create task: {str(e)}"}


async def complete_todo_task(client: GraphServiceClient, list_name: str, task_title: str) -> dict:
    """
    Mark a task as completed in a Microsoft To Do list.
    
    Args:
        client: Authenticated Graph API client
        list_name: Name of the To Do list
        task_title: Title of the task to complete
        
    Returns:
        dict: Updated task information or error message
    """
    try:
        task_lists = await _graph_call(client.me.todo.lists.get(), "Graph API call")
        target_list = None
        if task_lists and task_lists.value:
            for tl in task_lists.value:
                if tl.display_name and tl.display_name.lower() == list_name.lower():
                    target_list = tl
                    break
        
        if not target_list or not target_list.id:
            return {"error": f"Task list '{list_name}' not found."}

        tasks = await _graph_call(client.me.todo.lists.by_todo_task_list_id(target_list.id).tasks.get(), "Graph API call")
        target_task = None
        if tasks and tasks.value:
            for t in tasks.value:
                if t.title and t.title.lower() == task_title.lower():
                    target_task = t
                    break
        
        if not target_task or not target_task.id:
            return {"error": f"Task '{task_title}' not found in list '{list_name}'."}

        update = TodoTask()
        update.status = TaskStatus.Completed
        updated = await _graph_call(client.me.todo.lists.by_todo_task_list_id(target_list.id).tasks.by_todo_task_id(target_task.id).patch(update), "Graph API call")
        if updated:
            _cache_invalidate("read:todo")
            return {"title": updated.title, "status": updated.status.value if updated.status else "unknown"}
        return {"error": "Failed to update task."}
    except Exception as e:
        logger.error(f"Failed to complete todo task: {e}")
        return {"error": f"Failed to complete task: {str(e)}"}


async def update_todo_task(
    client: GraphServiceClient,
    list_id: str,
    task_id: str,
    title: str | None = None,
    due_date: str | None = None,
    status: str | None = None,
) -> dict:
    """
    Update an existing Microsoft To Do task by ID.

    Args:
        client: Authenticated Graph API client
        list_id: To Do list ID
        task_id: To Do task ID
        title: Optional updated title
        due_date: Optional updated due date (ISO 8601)
        status: Optional updated status string

    Returns:
        dict: Update status or error
    """
    try:
        update = TodoTask()

        if title is not None:
            update.title = title
        if due_date is not None:
            due = DateTimeTimeZone()
            due.date_time = due_date
            due.time_zone = "UTC"
            update.due_date_time = due
        if status is not None:
            status_map = {
                TodoStatus.NOT_STARTED.value: TaskStatus.NotStarted,
                TodoStatus.IN_PROGRESS.value: TaskStatus.InProgress,
                TodoStatus.COMPLETED.value: TaskStatus.Completed,
                TodoStatus.WAITING_ON_OTHERS.value: TaskStatus.WaitingOnOthers,
                TodoStatus.DEFERRED.value: TaskStatus.Deferred,
            }
            mapped = status_map.get(status)
            if mapped is None:
                return {"error": "Invalid status. Use one of: notStarted, inProgress, completed, waitingOnOthers, deferred."}
            update.status = mapped

        updated = await _graph_call(client.me.todo.lists.by_todo_task_list_id(list_id).tasks.by_todo_task_id(task_id).patch(update), "Graph API call")
        _cache_invalidate("read:todo")
        return {
            "status": "updated",
            "list_id": list_id,
            "task_id": updated.id if updated and updated.id else task_id,
        }
    except Exception as e:
        logger.error(f"Failed to update todo task: {e}")
        return {"error": f"Failed to update todo task: {str(e)}"}


async def delete_todo_task(client: GraphServiceClient, list_id: str, task_id: str) -> dict:
    """
    Delete a Microsoft To Do task.

    Args:
        client: Authenticated Graph API client
        list_id: To Do list ID
        task_id: To Do task ID

    Returns:
        dict: Delete status or error
    """
    try:
        await _graph_call(client.me.todo.lists.by_todo_task_list_id(list_id).tasks.by_todo_task_id(task_id).delete(), "Graph API call")
        _cache_invalidate("read:todo")
        return {
            "status": "deleted",
            "list_id": list_id,
            "task_id": task_id,
        }
    except Exception as e:
        logger.error(f"Failed to delete todo task: {e}")
        return {"error": f"Failed to delete todo task: {str(e)}"}


async def create_todo_list(client: GraphServiceClient, display_name: str) -> dict:
    """
    Create a Microsoft To Do list.

    Args:
        client: Authenticated Graph API client
        display_name: New list display name

    Returns:
        dict: Create status or error
    """
    try:
        todo_list = TodoTaskList()
        todo_list.display_name = display_name

        created = await _graph_call(client.me.todo.lists.post(todo_list), "Graph API call")
        if not created:
            return {"error": "Failed to create todo list."}

        _cache_invalidate("read:todo")

        return {
            "status": "created",
            "list": {
                "id": created.id,
                "display_name": created.display_name,
            },
        }
    except Exception as e:
        logger.error(f"Failed to create todo list: {e}")
        return {"error": f"Failed to create todo list: {str(e)}"}


# Email / Mail

async def get_messages(client: GraphServiceClient, top: int = 25, mailbox: str | None = None) -> list[dict]:
    """
    Get the user's most recent Exchange Online messages.
    
    Args:
        client: Authenticated Graph API client
        top: Number of messages to retrieve
        mailbox: Optional email address of a shared mailbox to read from (requires Full Access permissions)
        
    Returns:
        list[dict]: List of messages or empty list on error
    """
    try:
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            select=["id", "subject", "from", "receivedDateTime", "isRead"],
            orderby=["receivedDateTime desc"],
            top=top,
        )
        request_config = RequestConfiguration[MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters](
            query_parameters=query_params,
        )
        # Use shared mailbox if specified, otherwise use authenticated user's mailbox
        if mailbox:
            messages = await _graph_call(client.users.by_user_id(mailbox).messages.get(request_configuration=request_config), "Graph API call")
        else:
            messages = await _graph_call(client.me.messages.get(request_configuration=request_config), "Graph API call")
        results = []
        if messages and messages.value:
            for msg in messages.value:
                results.append({
                    "id": msg.id,
                    "received": str(msg.received_date_time),
                    "is_read": msg.is_read,
                    "from": msg.from_.email_address.address if msg.from_ and msg.from_.email_address else "Unknown",
                    "subject": msg.subject,
                })
        return results
    except Exception as e:
        logger.error(f"Failed to get messages: {e}")
        return [{"error": f"Failed to get messages: {str(e)}"}]


async def send_message(client: GraphServiceClient, to: str, subject: str, body: str, content_type: str = "text", from_address: str | None = None) -> dict:
    """
    Send an email message.
    
    Args:
        client: Authenticated Graph API client
        to: Recipient email address
        subject: Email subject
        body: Email body text
        content_type: Content type of the email body ("text" or "html"). Defaults to "text".
        from_address: Email address to send from (requires appropriate permissions). If not specified, sends from authenticated user.
        
    Returns:
        dict: Status message or error
    """
    try:
        msg = Message()
        msg.subject = subject
        
        # Set content type based on parameter
        body_type = BodyType.Html if content_type.lower() == ContentType.HTML.value else BodyType.Text
        msg.body = ItemBody(content=body, content_type=body_type)
        
        recipient = Recipient(email_address=EmailAddress(address=to))
        msg.to_recipients = [recipient]
        
        # Set from address if specified (requires appropriate permissions)
        if from_address:
            msg.from_ = Recipient(email_address=EmailAddress(address=from_address))

        request_body = SendMailPostRequestBody()
        request_body.message = msg
        request_body.save_to_sent_items = True
        await _graph_call(client.me.send_mail.post(request_body), "Graph API call")
        return {"status": "sent", "to": to, "subject": subject, "content_type": content_type, "from": from_address or "authenticated user"}
    except Exception as e:
        log_event(
            logger,
            logging.ERROR,
            "mail_send_failed",
            "Failed to send message",
            to=to,
            subject=subject,
            error=str(e),
        )
        return {"error": f"Failed to send message: {str(e)}"}


async def search_messages(client: GraphServiceClient, query: str, top: int = 25, mailbox: str | None = None) -> list[dict]:
    """
    Search the user's mailbox using a keyword query.
    
    Args:
        client: Authenticated Graph API client
        query: Search keywords
        top: Maximum number of results
        mailbox: Optional email address of a shared mailbox to search (requires Full Access permissions)
        
    Returns:
        list[dict]: List of matching messages or empty list on error
    """
    try:
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            search=f'"{query}"',  # Fixed: removed extra space
            select=["id", "subject", "from", "receivedDateTime", "isRead", "bodyPreview"],
            top=top,
        )
        request_config = RequestConfiguration[MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters](
            query_parameters=query_params,
        )
        # Use shared mailbox if specified, otherwise use authenticated user's mailbox
        if mailbox:
            messages = await _graph_call(client.users.by_user_id(mailbox).messages.get(request_configuration=request_config), "Graph API call")
        else:
            messages = await _graph_call(client.me.messages.get(request_configuration=request_config), "Graph API call")
        results = []
        if messages and messages.value:
            for msg in messages.value:
                results.append({
                    "id": msg.id,
                    "received": str(msg.received_date_time),
                    "is_read": msg.is_read,
                    "from": msg.from_.email_address.address if msg.from_ and msg.from_.email_address else "Unknown",
                    "subject": msg.subject,
                    "preview": msg.body_preview,
                })
        return results
    except Exception as e:
        logger.error(f"Failed to search messages: {e}")
        return [{"error": f"Failed to search messages: {str(e)}"}]


async def get_message_by_id(client: GraphServiceClient, message_id: str, mailbox: str | None = None) -> dict:
    """
    Retrieve a single Exchange Online email message by its Graph API message ID.

    Args:
        client: Authenticated Graph API client
        message_id: The Graph API message ID
        mailbox: Optional email address of a shared mailbox (requires Full Access permissions)

    Returns:
        dict: Full message details or error message
    """
    try:
        query_params = MessageItemRequestBuilder.MessageItemRequestBuilderGetQueryParameters(
            select=["subject", "from", "receivedDateTime", "isRead", "body",
                    "toRecipients", "ccRecipients", "hasAttachments", "internetMessageHeaders"],
        )
        request_config = MessageItemRequestBuilder.MessageItemRequestBuilderGetRequestConfiguration(
            query_parameters=query_params,
        )
        if mailbox:
            msg = await _graph_call(client.users.by_user_id(mailbox).messages.by_message_id(message_id).get(request_configuration=request_config), "Graph API call")
        else:
            msg = await _graph_call(client.me.messages.by_message_id(message_id).get(request_configuration=request_config), "Graph API call")

        if not msg:
            return {"error": "Message not found."}

        # Extract body type and content
        body_type = ContentType.HTML.value if msg.body and msg.body.content_type == BodyType.Html else ContentType.TEXT.value
        body_content = msg.body.content if msg.body else ""

        # Extract recipient email addresses
        to_list = [
            r.email_address.address
            for r in (msg.to_recipients or [])
            if r.email_address and r.email_address.address
        ]
        cc_list = [
            r.email_address.address
            for r in (msg.cc_recipients or [])
            if r.email_address and r.email_address.address
        ]

        # Extract RFC 822 Message-ID from internet message headers
        internet_message_id = None
        if msg.internet_message_headers:
            for header in msg.internet_message_headers:
                if header.name and header.name.lower() == "message-id":
                    internet_message_id = header.value
                    break

        return {
            "id": msg.id,
            "received": str(msg.received_date_time),
            "is_read": msg.is_read,
            "from": msg.from_.email_address.address if msg.from_ and msg.from_.email_address else "Unknown",
            "to": to_list,
            "cc": cc_list,
            "subject": msg.subject,
            "body_type": body_type,
            "body": body_content,
            "has_attachments": msg.has_attachments,
            "internet_message_id": internet_message_id,
        }
    except Exception as e:
        logger.error(f"Failed to get message by ID: {e}")
        return {"error": f"Failed to get message by ID: {str(e)}"}


async def reply_to_message(
    client: GraphServiceClient,
    message_id: str,
    body: str,
    content_type: str = "text",
    reply_all: bool = False,
    mailbox: str | None = None,
) -> dict:
    """
    Reply to an existing Exchange Online message.

    Args:
        client: Authenticated Graph API client
        message_id: Graph API message ID
        body: Reply body text
        content_type: Message content type hint (text|html)
        reply_all: Whether to reply to all recipients
        mailbox: Optional email address of a shared mailbox

    Returns:
        dict: Send status or error
    """
    try:
        if not body or not body.strip():
            exc = ValidationError("Reply body cannot be empty.")
            return exc.to_dict()

        target = (
            client.users.by_user_id(mailbox).messages.by_message_id(message_id)
            if mailbox
            else client.me.messages.by_message_id(message_id)
        )

        # Graph reply comment content is plain-text; keep content_type for caller visibility.
        if reply_all:
            request_body = ReplyAllPostRequestBody()
            request_body.comment = body
            await _graph_call(target.reply_all.post(request_body), "Reply all to message")
        else:
            request_body = ReplyPostRequestBody()
            request_body.comment = body
            await _graph_call(target.reply.post(request_body), "Reply to message")

        return {
            "status": "sent",
            "message_id": message_id,
            "reply_all": reply_all,
            "mailbox": mailbox,
            "content_type": content_type,
        }
    except asyncio.TimeoutError:
        exc = M365TimeoutError("Reply operation timed out after 30 seconds")
        logger.warning(f"Graph API timeout: {exc.message}")
        return exc.to_dict()
    except Exception as e:
        exc = error_from_graph_exception(e)
        logger.error(f"Failed to reply to message: {exc.message}")
        return exc.to_dict()


async def forward_message(
    client: GraphServiceClient,
    message_id: str,
    to: list[str],
    comment: str | None = None,
    mailbox: str | None = None,
) -> dict:
    """
    Forward a message to one or more recipients.

    Args:
        client: Authenticated Graph API client
        message_id: Message ID to forward
        to: List of recipient email addresses
        comment: Optional forwarding comment
        mailbox: Optional mailbox identifier

    Returns:
        dict: Forward status or error
    """
    try:
        to_recipients = []
        for email in to:
            recipient = Recipient()
            recipient.email_address = EmailAddress(address=email)
            to_recipients.append(recipient)

        req_body = ForwardPostRequestBody()
        req_body.to_recipients = to_recipients
        if comment:
            req_body.comment = comment

        await asyncio.wait_for(
            client.me.messages.by_message_id(message_id).forward.post(req_body),
            timeout=30
        )
        return {
            "status": "sent",
            "message_id": message_id,
            "to": to,
            "mailbox": mailbox,
        }
    except asyncio.TimeoutError:
        exc = M365TimeoutError("Forward operation timed out after 30 seconds")
        logger.warning(f"Graph API timeout: {exc.message}")
        return exc.to_dict()
    except Exception as e:
        exc = error_from_graph_exception(e)
        logger.error(f"Failed to forward message: {exc.message}")
        return exc.to_dict()


async def mark_message_read(
    client: GraphServiceClient,
    message_id: str,
    is_read: bool = True,
    mailbox: str | None = None,
) -> dict:
    """
    Mark a message read or unread.

    Args:
        client: Authenticated Graph API client
        message_id: Graph API message ID
        is_read: Desired read state
        mailbox: Optional email address of a shared mailbox

    Returns:
        dict: Update status or error
    """
    try:
        target = (
            client.users.by_user_id(mailbox).messages.by_message_id(message_id)
            if mailbox
            else client.me.messages.by_message_id(message_id)
        )

        update = Message()
        update.is_read = is_read
        updated = await _graph_call(target.patch(update), "Graph API call")

        return {
            "status": "updated",
            "message_id": updated.id if updated and updated.id else message_id,
            "is_read": updated.is_read if updated and updated.is_read is not None else is_read,
            "mailbox": mailbox,
        }
    except Exception as e:
        logger.error(f"Failed to mark message read state: {e}")
        return {"error": f"Failed to mark message read state: {str(e)}"}


async def list_mail_folders(
    client: GraphServiceClient,
    top: int = 100,
    mailbox: str | None = None,
) -> list[dict]:
    """
    List mail folders and metadata for the current or shared mailbox.

    Args:
        client: Authenticated Graph API client
        top: Maximum number of folders to return
        mailbox: Optional email address of a shared mailbox

    Returns:
        list[dict]: List of mail folders or error payload
    """
    try:
        safe_top = max(1, min(top, 200))
        query_params = MailFoldersRequestBuilder.MailFoldersRequestBuilderGetQueryParameters(
            select=["id", "displayName", "totalItemCount", "unreadItemCount"],
            top=safe_top,
        )
        request_config = RequestConfiguration[MailFoldersRequestBuilder.MailFoldersRequestBuilderGetQueryParameters](
            query_parameters=query_params,
        )

        folders = (
            await _graph_call(client.users.by_user_id(mailbox).mail_folders.get(request_configuration=request_config), "Graph API call")
            if mailbox
            else await _graph_call(client.me.mail_folders.get(request_configuration=request_config), "Graph API call")
        )

        results = []
        if folders and folders.value:
            for folder in folders.value:
                results.append({
                    "id": folder.id,
                    "display_name": folder.display_name,
                    "total_item_count": folder.total_item_count,
                    "unread_item_count": folder.unread_item_count,
                })
        return results
    except Exception as e:
        logger.error(f"Failed to list mail folders: {e}")
        return [{"error": f"Failed to list mail folders: {str(e)}"}]


async def move_message(
    client: GraphServiceClient,
    message_id: str,
    destination_folder_id: str,
    mailbox: str | None = None,
) -> dict:
    """
    Move a message to a target mail folder.

    Args:
        client: Authenticated Graph API client
        message_id: Graph API message ID
        destination_folder_id: Target mail folder ID
        mailbox: Optional email address of a shared mailbox

    Returns:
        dict: Move status or error
    """
    try:
        target = (
            client.users.by_user_id(mailbox).messages.by_message_id(message_id)
            if mailbox
            else client.me.messages.by_message_id(message_id)
        )

        request_body = MovePostRequestBody()
        request_body.destination_id = destination_folder_id
        moved = await _graph_call(target.move.post(request_body), "Graph API call")

        return {
            "status": "moved",
            "source_message_id": message_id,
            "destination_message_id": moved.id if moved else None,
            "destination_folder_id": destination_folder_id,
            "mailbox": mailbox,
        }
    except Exception as e:
        logger.error(f"Failed to move message: {e}")
        return {"error": f"Failed to move message: {str(e)}"}


async def get_message_attachments(
    client: GraphServiceClient,
    message_id: str,
    mailbox: str | None = None,
) -> dict:
    """
    List attachment metadata for a message.

    Args:
        client: Authenticated Graph API client
        message_id: Graph API message ID
        mailbox: Optional email address of a shared mailbox

    Returns:
        dict: Attachment list or error
    """
    try:
        query_params = AttachmentsRequestBuilder.AttachmentsRequestBuilderGetQueryParameters(
            select=["id", "name", "contentType", "size", "isInline", "@odata.type"],
            top=200,
        )
        request_config = RequestConfiguration[AttachmentsRequestBuilder.AttachmentsRequestBuilderGetQueryParameters](
            query_parameters=query_params,
        )

        attachments = (
            await _graph_call(
                client.users.by_user_id(mailbox).messages.by_message_id(message_id).attachments.get(
                    request_configuration=request_config,
                ),
                "Get message attachments from mailbox",
            )
            if mailbox
            else await _graph_call(
                client.me.messages.by_message_id(message_id).attachments.get(
                    request_configuration=request_config,
                ),
                "Get message attachments",
            )
        )

        results = []
        if attachments and attachments.value:
            for attachment in attachments.value:
                results.append({
                    "id": attachment.id,
                    "name": attachment.name,
                    "content_type": attachment.content_type,
                    "size": attachment.size,
                    "is_inline": attachment.is_inline,
                    "odata_type": attachment.odata_type,
                })

        return {
            "message_id": message_id,
            "attachments": results,
            "mailbox": mailbox,
        }
    except Exception as e:
        logger.error(f"Failed to get message attachments: {e}")
        return {"error": f"Failed to get message attachments: {str(e)}"}


# Calendar

async def get_calendar_events(client: GraphServiceClient, days: int = 7) -> list[dict]:
    """
    Get the user's calendar events for the next N days.
    
    Args:
        client: Authenticated Graph API client
        days: Number of days ahead to fetch events for
        
    Returns:
        list[dict]: List of calendar events or empty list on error
    """
    try:
        cache_key = f"read:calendar_events:{days}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        now = datetime.now(timezone.utc)
        start = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        end = (now + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

        query_params = CalendarViewRequestBuilder.CalendarViewRequestBuilderGetQueryParameters(
            start_date_time=start,
            end_date_time=end,
            select=["subject", "start", "end", "location", "organizer", "isAllDay"],
            orderby=["start/dateTime"],
            top=50,
        )
        request_config = RequestConfiguration[CalendarViewRequestBuilder.CalendarViewRequestBuilderGetQueryParameters](
            query_parameters=query_params,
        )
        events = await _graph_call(client.me.calendar_view.get(request_configuration=request_config), "Graph API call")
        results = []
        if events and events.value:
            for event in events.value:
                results.append({
                    "subject": event.subject,
                    "start": event.start.date_time if event.start else None,
                    "end": event.end.date_time if event.end else None,
                    "is_all_day": event.is_all_day,
                    "location": event.location.display_name if event.location and event.location.display_name else None,
                    "organizer": event.organizer.email_address.name if event.organizer and event.organizer.email_address else "Unknown",
                })
        return _cache_set(cache_key, results)
    except Exception as e:
        logger.error(f"Failed to get calendar events: {e}")
        return [{"error": f"Failed to get calendar events: {str(e)}"}]


async def create_calendar_event(
    client: GraphServiceClient,
    subject: str,
    start: str,
    end: str,
    attendees: Optional[list[str]] = None,
    location: Optional[str] = None,
    body: Optional[str] = None,
    is_all_day: bool = False
) -> dict:
    """
    Create a new calendar event.
    
    Args:
        client: Authenticated Graph API client
        subject: Event title
        start: Start time in ISO 8601 format
        end: End time in ISO 8601 format
        attendees: Optional list of attendee email addresses
        location: Optional location name
        body: Optional event description
        is_all_day: Whether this is an all-day event
        
    Returns:
        dict: Created event information or error message
    """
    try:
        event = Event()
        event.subject = subject
        event.start = DateTimeTimeZone(date_time=start, time_zone="UTC")
        event.end = DateTimeTimeZone(date_time=end, time_zone="UTC")
        event.is_all_day = is_all_day

        if body:
            event.body = ItemBody(content=body, content_type=BodyType.Text)
        if location:
            event.location = Location(display_name=location)
        if attendees:
            event.attendees = [
                Attendee(
                    email_address=EmailAddress(address=a),
                    type=AttendeeType.Required,
                )
                for a in attendees
            ]

        created = await _graph_call(client.me.events.post(event), "Graph API call")
        if created:
            _cache_invalidate("read:calendar_events")
            return {
                "id": created.id,
                "subject": created.subject,
                "start": created.start.date_time if created.start else None,
                "end": created.end.date_time if created.end else None,
            }
        return {"error": "Failed to create event."}
    except Exception as e:
        log_event(
            logger,
            logging.ERROR,
            "calendar_event_create_failed",
            "Failed to create calendar event",
            subject=subject,
            start=start,
            end=end,
            error=str(e),
        )
        return {"error": f"Failed to create event: {str(e)}"}


async def update_calendar_event(
    client: GraphServiceClient,
    event_id: str,
    subject: str | None = None,
    start: str | None = None,
    end: str | None = None,
    attendees: Optional[list[str]] = None,
    location: str | None = None,
    body: str | None = None,
    is_all_day: bool | None = None,
) -> dict:
    """
    Update an existing calendar event.

    Args:
        client: Authenticated Graph API client
        event_id: Calendar event ID
        subject: Optional event subject
        start: Optional event start time (ISO 8601)
        end: Optional event end time (ISO 8601)
        attendees: Optional list of attendee email addresses
        location: Optional location name
        body: Optional event body text
        is_all_day: Optional all-day flag

    Returns:
        dict: Update status or error
    """
    try:
        update = Event()

        if subject is not None:
            update.subject = subject
        if start is not None:
            update.start = DateTimeTimeZone(date_time=start, time_zone="UTC")
        if end is not None:
            update.end = DateTimeTimeZone(date_time=end, time_zone="UTC")
        if attendees is not None:
            update.attendees = [
                Attendee(
                    email_address=EmailAddress(address=a),
                    type=AttendeeType.Required,
                )
                for a in attendees
            ]
        if location is not None:
            update.location = Location(display_name=location)
        if body is not None:
            update.body = ItemBody(content=body, content_type=BodyType.Text)
        if is_all_day is not None:
            update.is_all_day = is_all_day

        updated = await _graph_call(client.me.events.by_event_id(event_id).patch(update), "Graph API call")
        _cache_invalidate("read:calendar_events")

        return {
            "status": "updated",
            "event_id": updated.id if updated and updated.id else event_id,
            "subject": updated.subject if updated else subject,
            "start": updated.start.date_time if updated and updated.start else start,
            "end": updated.end.date_time if updated and updated.end else end,
        }
    except Exception as e:
        log_event(
            logger,
            logging.ERROR,
            "calendar_event_update_failed",
            "Failed to update calendar event",
            event_id=event_id,
            error=str(e),
        )
        return {"error": f"Failed to update calendar event: {str(e)}"}


async def delete_calendar_event(client: GraphServiceClient, event_id: str) -> dict:
    """
    Delete a calendar event.

    Args:
        client: Authenticated Graph API client
        event_id: Calendar event ID

    Returns:
        dict: Delete status or error
    """
    try:
        await _graph_call(client.me.events.by_event_id(event_id).delete(), "Graph API call")
        _cache_invalidate("read:calendar_events")
        return {
            "status": "deleted",
            "event_id": event_id,
        }
    except Exception as e:
        logger.error(f"Failed to delete calendar event: {e}")
        return {"error": f"Failed to delete calendar event: {str(e)}"}


async def respond_to_event(
    client: GraphServiceClient,
    event_id: str,
    response: str,
    comment: str | None = None,
    send_response: bool = True,
) -> dict:
    """
    Respond to a meeting invitation.

    Args:
        client: Authenticated Graph API client
        event_id: Calendar event ID
        response: accept|decline|tentative
        comment: Optional response comment
        send_response: Whether to send response notifications

    Returns:
        dict: Response status or error
    """
    try:
        normalized = response.strip().lower()
        target = client.me.events.by_event_id(event_id)

        if normalized == EventResponse.ACCEPT.value:
            request_body = AcceptPostRequestBody()
            request_body.comment = comment
            request_body.send_response = send_response
            await _graph_call(target.accept.post(request_body), "Graph API call")
        elif normalized == EventResponse.DECLINE.value:
            request_body = DeclinePostRequestBody()
            request_body.comment = comment
            request_body.send_response = send_response
            await _graph_call(target.decline.post(request_body), "Graph API call")
        elif normalized == EventResponse.TENTATIVE.value:
            request_body = TentativelyAcceptPostRequestBody()
            request_body.comment = comment
            request_body.send_response = send_response
            await _graph_call(target.tentatively_accept.post(request_body), "Graph API call")
        else:
            return {"error": "Invalid response. Use one of: accept, decline, tentative."}

        _cache_invalidate("read:calendar_events")
        return {
            "status": "responded",
            "event_id": event_id,
            "response": normalized,
            "send_response": send_response,
        }
    except Exception as e:
        log_event(
            logger,
            logging.ERROR,
            "calendar_event_response_failed",
            "Failed to respond to event",
            event_id=event_id,
            response=response,
            error=str(e),
        )
        return {"error": f"Failed to respond to event: {str(e)}"}


async def find_meeting_times(
    client: GraphServiceClient,
    attendees: list[str],
    duration_minutes: int,
    time_window_start: str,
    time_window_end: str,
    max_candidates: int = 10,
) -> dict:
    """
    Find candidate meeting times based on attendee availability.

    Args:
        client: Authenticated Graph API client
        attendees: List of attendee email addresses
        duration_minutes: Desired meeting duration in minutes
        time_window_start: Search window start time (ISO 8601)
        time_window_end: Search window end time (ISO 8601)
        max_candidates: Maximum number of candidate windows to return

    Returns:
        dict: Candidate suggestions or error
    """
    try:
        if not attendees:
            return {"error": "At least one attendee is required."}
        if duration_minutes <= 0:
            return {"error": "duration_minutes must be greater than 0."}

        request_body = GetSchedulePostRequestBody()
        request_body.schedules = attendees
        request_body.start_time = DateTimeTimeZone(date_time=time_window_start, time_zone="UTC")
        request_body.end_time = DateTimeTimeZone(date_time=time_window_end, time_zone="UTC")
        request_body.availability_view_interval = max(5, min(duration_minutes, 1440))

        schedule_response = await _graph_call(client.me.calendar.get_schedule.post(request_body), "Graph API call")
        schedule_infos = schedule_response.value if schedule_response and schedule_response.value else []

        suggestions = []
        for info in schedule_infos:
            for item in info.schedule_items or []:
                suggestions.append({
                    "attendee": info.schedule_id,
                    "status": item.status.value if item.status else None,
                    "start": item.start.date_time if item.start else None,
                    "end": item.end.date_time if item.end else None,
                    "subject": item.subject,
                    "location": item.location,
                    "is_private": item.is_private,
                })

        suggestions_sorted = sorted(
            suggestions,
            key=lambda x: x["start"] or "",
        )

        return {
            "suggestions": suggestions_sorted[: max(1, min(max_candidates, 50))],
            "window_start": time_window_start,
            "window_end": time_window_end,
            "duration_minutes": duration_minutes,
        }
    except Exception as e:
        logger.error(f"Failed to find meeting times: {e}")
        return {"error": f"Failed to find meeting times: {str(e)}"}


# Contacts

async def get_contacts(client: GraphServiceClient, top: int = 25) -> list[dict]:
    """
    Get the user's contacts from their address book.
    
    Args:
        client: Authenticated Graph API client
        top: Maximum number of contacts to return
        
    Returns:
        list[dict]: List of contacts or empty list on error
    """
    try:
        cache_key = f"read:contacts:{top}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        query_params = ContactsRequestBuilder.ContactsRequestBuilderGetQueryParameters(
            select=["displayName", "emailAddresses", "mobilePhone", "businessPhones", "companyName", "jobTitle"],
            top=top,
        )
        request_config = RequestConfiguration[ContactsRequestBuilder.ContactsRequestBuilderGetQueryParameters](
            query_parameters=query_params,
        )
        contacts = await _graph_call(client.me.contacts.get(request_configuration=request_config), "Graph API call")
        results = []
        if contacts and contacts.value:
            for c in contacts.value:
                emails = [e.address for e in c.email_addresses] if c.email_addresses else []
                results.append({
                    "name": c.display_name,
                    "emails": emails,
                    "mobile": c.mobile_phone,
                    "business_phones": c.business_phones,
                    "company": c.company_name,
                    "job_title": c.job_title,
                })
        return _cache_set(cache_key, results)
    except Exception as e:
        logger.error(f"Failed to get contacts: {e}")
        return [{"error": f"Failed to get contacts: {str(e)}"}]


# Files (OneDrive)

async def get_recent_files(client: GraphServiceClient, top: int = 25) -> list[dict]:
    """
    Get the user's recently accessed OneDrive files.
    
    Args:
        client: Authenticated Graph API client
        top: Maximum number of files to return
        
    Returns:
        list[dict]: List of recent files or empty list on error
    """
    try:
        cache_key = f"read:recent_files:{top}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        drive = await _graph_call(client.me.drive.get(), "Graph API call")
        if not drive or not drive.id:
            return [{"error": "Could not access user's drive."}]

        children_builder = getattr(client.drives.by_drive_id(drive.id).root, "children")
        children_resp = await _graph_call(children_builder.get(), "Graph API call")
        items = children_resp.value if children_resp and children_resp.value else []

        # Sort by last_modified_date_time (newest first), tolerating None values
        items_sorted = sorted(items, key=lambda it: it.last_modified_date_time or datetime.min, reverse=True)

        results = []
        for item in items_sorted[:top]:
            results.append({
                "name": item.name,
                "web_url": item.web_url,
                "size": item.size,
                "last_modified": str(item.last_modified_date_time) if item.last_modified_date_time else None,
            })
        return _cache_set(cache_key, results)
    except Exception as e:
        log_event(
            logger,
            logging.ERROR,
            "recent_files_fetch_failed",
            "Failed to get recent files",
            top=top,
            error=str(e),
        )
        return [{"error": f"Failed to get recent files: {str(e)}"}]


async def search_files(client: GraphServiceClient, query: str, top: int = 25) -> list[dict]:
    """
    Search for files in OneDrive and SharePoint by keyword.
    
    Args:
        client: Authenticated Graph API client
        query: Search keywords
        top: Maximum number of results
        
    Returns:
        list[dict]: List of matching files or empty list on error
    """
    try:
        drive = await _graph_call(client.me.drive.get(), "Graph API call")
        if not drive or not drive.id:
            return [{"error": "Could not access user's drive."}]

        search_results = await _graph_call(client.drives.by_drive_id(drive.id).search_with_q(q=query).get(), "Graph API call")
        results = []
        if search_results and search_results.value:
            for item in search_results.value[:top]:
                results.append({
                    "name": item.name,
                    "web_url": item.web_url,
                    "size": item.size,
                    "last_modified": str(item.last_modified_date_time) if item.last_modified_date_time else None,
                })
        return results
    except Exception as e:
        logger.error(f"Failed to search files: {e}")
        return [{"error": f"Failed to search files: {str(e)}"}]


async def list_drive_items(client: GraphServiceClient, item_id: str | None = None, top: int = 50) -> dict:
    """
    List OneDrive folder contents from root or a specific folder item.

    Args:
        client: Authenticated Graph API client
        item_id: Optional folder item ID; if omitted, root is used
        top: Maximum number of items to return

    Returns:
        dict: Folder listing payload or error
    """
    try:
        drive = await _graph_call(client.me.drive.get(), "Graph API call")
        if not drive or not drive.id:
            return {"error": "Could not access user's drive."}

        safe_top = max(1, min(top, 200))
        query_params = ChildrenRequestBuilder.ChildrenRequestBuilderGetQueryParameters(
            select=["id", "name", "folder", "size", "webUrl", "lastModifiedDateTime"],
            top=safe_top,
        )
        request_config = RequestConfiguration[ChildrenRequestBuilder.ChildrenRequestBuilderGetQueryParameters](
            query_parameters=query_params,
        )

        if item_id:
            children = await _graph_call(
                client.drives.by_drive_id(drive.id).items.by_drive_item_id(item_id).children.get(
                    request_configuration=request_config,
                ),
                "List drive children by item",
            )
        else:
            children = await _graph_call(
                client.drives.by_drive_id(drive.id).root.children.get(
                    request_configuration=request_config,
                ),
                "List drive root children",
            )

        items = []
        if children and children.value:
            for item in children.value:
                items.append({
                    "id": item.id,
                    "name": item.name,
                    "is_folder": bool(item.folder),
                    "size": item.size,
                    "web_url": item.web_url,
                    "last_modified": str(item.last_modified_date_time) if item.last_modified_date_time else None,
                })

        return {
            "items": items,
            "next_link": getattr(children, "odata_next_link", None),
        }
    except Exception as e:
        logger.error(f"Failed to list drive items: {e}")
        return {"error": f"Failed to list drive items: {str(e)}"}


async def create_share_link(
    client: GraphServiceClient,
    item_id: str,
    link_type: str = "view",
    scope: str = "organization",
) -> dict:
    """
    Create a share link for a OneDrive file/folder.

    Args:
        client: Authenticated Graph API client
        item_id: Drive item ID
        link_type: Link type (view|edit)
        scope: Link scope (organization|anonymous)

    Returns:
        dict: Share-link metadata or error
    """
    try:
        drive = await _graph_call(client.me.drive.get(), "Graph API call")
        if not drive or not drive.id:
            return {"error": "Could not access user's drive."}

        request_body = CreateLinkPostRequestBody()
        request_body.type = link_type
        request_body.scope = scope

        permission = await _graph_call(client.drives.by_drive_id(drive.id).items.by_drive_item_id(item_id).create_link.post(request_body), "Graph API call")
        web_url = permission.link.web_url if permission and permission.link else None

        return {
            "status": "created",
            "item_id": item_id,
            "web_url": web_url,
            "link_type": link_type,
            "scope": scope,
        }
    except Exception as e:
        logger.error(f"Failed to create share link: {e}")
        return {"error": f"Failed to create share link: {str(e)}"}


async def upload_small_text_file(
    client: GraphServiceClient,
    file_name: str,
    content: str,
    parent_item_id: str | None = None,
    content_type: str = "text/plain",
) -> dict:
    """
    Upload a small UTF-8 text file to OneDrive.

    Args:
        client: Authenticated Graph API client
        file_name: Destination file name
        content: Text content to upload
        parent_item_id: Optional parent folder item ID; root when omitted
        content_type: MIME type hint for content

    Returns:
        dict: Uploaded file metadata or error
    """
    try:
        drive = await _graph_call(client.me.drive.get(), "Graph API call")
        if not drive or not drive.id:
            return {"error": "Could not access user's drive."}

        drive_builder = client.drives.by_drive_id(drive.id)

        new_file = DriveItem()
        new_file.name = file_name
        new_file.file = File()

        if parent_item_id:
            created = await _graph_call(drive_builder.items.by_drive_item_id(parent_item_id).children.post(new_file), "Graph API call")
        else:
            created = await _graph_call(drive_builder.root.children.post(new_file), "Graph API call")

        if not created or not created.id:
            return {"error": "Failed to create file item in OneDrive."}

        uploaded = await _graph_call(
            drive_builder.items.by_drive_item_id(created.id).content.put(content.encode("utf-8")),
            "Upload file content",
        )
        item = uploaded or created

        _cache_invalidate("read:recent_files")
        return {
            "status": "uploaded",
            "item": {
                "id": item.id,
                "name": item.name,
                "web_url": item.web_url,
                "size": item.size,
            },
            "content_type": content_type,
        }
    except Exception as e:
        logger.error(f"Failed to upload small text file: {e}")
        return {"error": f"Failed to upload small text file: {str(e)}"}


# Teams

async def get_teams_chats(client: GraphServiceClient, top: int = 25) -> list[dict]:
    """
    Get the user's recent Teams chat threads.
    
    Args:
        client: Authenticated Graph API client
        top: Maximum number of chats to return
        
    Returns:
        list[dict]: List of chats or empty list on error
    """
    try:
        query_params = ChatsRequestBuilder.ChatsRequestBuilderGetQueryParameters(
            select=["id", "topic", "chatType", "lastUpdatedDateTime"],
            top=top,
        )
        request_config = RequestConfiguration[ChatsRequestBuilder.ChatsRequestBuilderGetQueryParameters](
            query_parameters=query_params,
        )
        chats = await _graph_call(client.me.chats.get(request_configuration=request_config), "Graph API call")
        results = []
        if chats and chats.value:
            for chat in chats.value:
                results.append({
                    "id": chat.id,
                    "topic": chat.topic,
                    "chat_type": chat.chat_type.value if chat.chat_type else None,
                    "last_updated": str(chat.last_updated_date_time) if chat.last_updated_date_time else None,
                })
        return results
    except Exception as e:
        logger.error(f"Failed to get teams chats: {e}")
        return [{"error": f"Failed to get teams chats: {str(e)}"}]


async def get_chat_messages(client: GraphServiceClient, chat_id: str, top: int = 25) -> list[dict]:
    """
    Get messages from a specific Teams chat.
    
    Args:
        client: Authenticated Graph API client
        chat_id: The ID of the Teams chat
        top: Maximum number of messages to return
        
    Returns:
        list[dict]: List of chat messages or empty list on error
    """
    try:
        query_params = ChatMessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            top=top,
        )
        request_config = RequestConfiguration[ChatMessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters](
            query_parameters=query_params,
        )
        messages = await _graph_call(client.me.chats.by_chat_id(chat_id).messages.get(request_configuration=request_config), "Graph API call")
        results = []
        if messages and messages.value:
            for msg in messages.value:
                results.append({
                    "id": msg.id,
                    "from": msg.from_.user.display_name if msg.from_ and msg.from_.user else "Unknown",
                    "created": str(msg.created_date_time) if msg.created_date_time else None,
                    "body": msg.body.content if msg.body else None,
                })
        return results
    except Exception as e:
        logger.error(f"Failed to get chat messages: {e}")
        return [{"error": f"Failed to get chat messages: {str(e)}"}]


async def get_chat_participants(client: GraphServiceClient, chat_id: str) -> dict:
    """
    Retrieve participants for a specific Teams chat.

    Args:
        client: Authenticated Graph API client
        chat_id: Teams chat ID

    Returns:
        dict: Participant payload or error
    """
    try:
        members = await _graph_call(client.me.chats.by_chat_id(chat_id).members.get(), "Graph API call")
        participants = []
        if members and members.value:
            for member in members.value:
                participant_id = getattr(member, "user_id", None) or getattr(member, "id", None)
                display_name = getattr(member, "display_name", None)
                email = getattr(member, "email", None)
                roles = getattr(member, "roles", None) or []
                participants.append(
                    {
                        "id": participant_id,
                        "display_name": display_name,
                        "email": email,
                        "roles": roles,
                    }
                )

        return {
            "chat_id": chat_id,
            "participants": participants,
        }
    except Exception as e:
        logger.error(f"Failed to get chat participants: {e}")
        return {"error": f"Failed to get chat participants: {str(e)}"}


async def send_chat_message(client: GraphServiceClient, message: str, recipient: str | None = None, chat_id: str | None = None, content_type: str = "text") -> dict:
    """
    Send a Teams chat message to a user or existing chat.
    
    Args:
        client: Authenticated Graph API client
        message: Message body text
        recipient: Recipient's email address (UPN) for 1:1 chat creation
        chat_id: Existing chat ID to send message to (group or 1:1)
        content_type: Content type of the message body ("text" or "html"). Defaults to "text".
        
    Returns:
        dict: Status message with chat details or error
    """
    try:
        # Validate parameters
        if not chat_id and not recipient:
            return {"error": "Either recipient or chat_id is required"}
        
        # Determine target chat ID
        if chat_id:
            # Use existing chat
            target_chat_id = chat_id
            target = chat_id
        else:
            # Create or get 1:1 chat with recipient
            assert recipient is not None  # guaranteed by the guard above
            me = await _graph_call(client.me.get(), "Graph API call")
            if not me or not me.id:
                return {"error": "Failed to get authenticated user information"}
            
            authenticated_user_id = me.id
            authenticated_user_email = me.mail or me.user_principal_name
            
            # Create or get 1:1 chat
            chat = Chat()
            chat.chat_type = ChatType.OneOnOne
            
            # Create members list - always add authenticated user first
            members: list[ConversationMember] = [
                AadUserConversationMember(
                    roles=["owner"],
                    additional_data={
                        "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{authenticated_user_id}')"
                    }
                )
            ]
            
            # Only add recipient as second member if they're different from authenticated user
            if authenticated_user_email is None or recipient.lower() != authenticated_user_email.lower():
                members.append(
                    AadUserConversationMember(
                        roles=["owner"],
                        additional_data={
                            "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{recipient}')"
                        }
                    )
                )
            
            chat.members = members
            
            created_chat = await _graph_call(client.chats.post(chat), "Graph API call")
            
            if not created_chat or not created_chat.id:
                return {"error": "Failed to create or retrieve chat"}
            
            target_chat_id = created_chat.id
            target = recipient
        
        # Send message to the chat
        body_type = BodyType.Html if content_type.lower() == ContentType.HTML.value else BodyType.Text
        chat_message = ChatMessage()
        chat_message.body = ItemBody(
            content_type=body_type,
            content=message
        )
        
        await _graph_call(client.chats.by_chat_id(target_chat_id).messages.post(chat_message), "Graph API call")
        _cache_invalidate("read:relevant_people")
        
        return {
            "status": "sent",
            "to": target,
            "chat_id": target_chat_id,
            "content_type": content_type
        }
    except Exception as e:
        log_event(
            logger,
            logging.ERROR,
            "chat_message_send_failed",
            "Failed to send chat message",
            recipient=recipient,
            chat_id=chat_id,
            error=str(e),
        )
        return {"error": f"Failed to send chat message: {str(e)}"}


async def send_channel_message(
    client: GraphServiceClient,
    team_id: str,
    channel_id: str,
    message: str,
    content_type: str = "text",
) -> dict:
    """
    Send a message to a Teams channel.

    Args:
        client: Authenticated Graph API client
        team_id: Team ID
        channel_id: Channel ID
        message: Message body
        content_type: Message content type (text|html)

    Returns:
        dict: Send status or error
    """
    try:
        body_type = BodyType.Html if content_type.lower() == ContentType.HTML.value else BodyType.Text
        chat_message = ChatMessage()
        chat_message.body = ItemBody(
            content_type=body_type,
            content=message,
        )

        created = await _graph_call(client.teams.by_team_id(team_id).channels.by_channel_id(channel_id).messages.post(chat_message), "Graph API call")
        _cache_invalidate("read:relevant_people")

        return {
            "status": "sent",
            "team_id": team_id,
            "channel_id": channel_id,
            "message_id": created.id if created and created.id else None,
            "content_type": content_type,
        }
    except Exception as e:
        log_event(
            logger,
            logging.ERROR,
            "channel_message_send_failed",
            "Failed to send channel message",
            team_id=team_id,
            channel_id=channel_id,
            error=str(e),
        )
        return {"error": f"Failed to send channel message: {str(e)}"}


async def get_teams_and_channels(client: GraphServiceClient) -> list[dict]:
    """
    List the user's joined Teams and their channels.
    
    Args:
        client: Authenticated Graph API client
        
    Returns:
        list[dict]: List of teams with their channels or empty list on error
    """
    try:
        teams = await _graph_call(client.me.joined_teams.get(), "Graph API call")
        results = []
        if teams and teams.value:
            for team in teams.value:
                team_info = {
                    "team_id": team.id,
                    "team_name": team.display_name,
                    "channels": [],
                }
                if team.id:
                    channels = await _graph_call(client.teams.by_team_id(team.id).channels.get(), "Graph API call")
                    if channels and channels.value:
                        for ch in channels.value:
                            team_info["channels"].append({
                                "channel_id": ch.id,
                                "name": ch.display_name,
                            })
                results.append(team_info)
        return results
    except Exception as e:
        logger.error(f"Failed to get teams and channels: {e}")
        return [{"error": f"Failed to get teams and channels: {str(e)}"}]


async def get_user_presence(client: GraphServiceClient, user_ids: Optional[list[str]] = None) -> list[dict]:
    """
    Get the presence status (available, busy, away, etc.) of users.
    
    Args:
        client: Authenticated Graph API client
        user_ids: Optional list of user IDs to check. If omitted, returns current user's presence.
        
    Returns:
        list[dict]: List of presence information or empty list on error
    """
    try:
        results = []
        if user_ids:
            request_body = GetPresencesByUserIdPostRequestBody(ids=user_ids)
            presences = await _graph_call(client.communications.get_presences_by_user_id.post(request_body), "Graph API call")
            if presences and presences.value:
                for p in presences.value:
                    results.append({
                        "user_id": p.id,
                        "availability": p.availability,
                        "activity": p.activity,
                    })
        else:
            presence = await _graph_call(client.me.presence.get(), "Graph API call")
            if presence:
                results.append({
                    "user_id": presence.id,
                    "availability": presence.availability,
                    "activity": presence.activity,
                })
        return results
    except Exception as e:
        logger.error(f"Failed to get user presence: {e}")
        return [{"error": f"Failed to get user presence: {str(e)}"}]


# Context & Intelligence

async def get_relevant_people(client: GraphServiceClient, top: int = 25) -> list[dict]:
    """
    Get people most relevant to the user (frequent contacts, collaborators).
    
    Args:
        client: Authenticated Graph API client
        top: Maximum number of people to return
        
    Returns:
        list[dict]: List of relevant people or empty list on error
    """
    try:
        cache_key = f"read:relevant_people:{top}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        query_params = PeopleRequestBuilder.PeopleRequestBuilderGetQueryParameters(
            top=top,
        )
        request_config = RequestConfiguration[PeopleRequestBuilder.PeopleRequestBuilderGetQueryParameters](
            query_parameters=query_params,
        )
        people = await _graph_call(client.me.people.get(request_configuration=request_config), "Graph API call")
        results = []
        if people and people.value:
            for person in people.value:
                emails = [e.address for e in person.scored_email_addresses] if person.scored_email_addresses else []
                results.append({
                    "name": person.display_name,
                    "emails": emails,
                    "job_title": person.job_title,
                    "department": person.department,
                    "company": person.company_name,
                })
        return _cache_set(cache_key, results)
    except Exception as e:
        log_event(
            logger,
            logging.ERROR,
            "relevant_people_fetch_failed",
            "Failed to get relevant people",
            top=top,
            error=str(e),
        )
        return [{"error": f"Failed to get relevant people: {str(e)}"}]


async def get_trending_files(client: GraphServiceClient, top: int = 25) -> list[dict]:
    """
    Get documents trending around the user.
    
    Args:
        client: Authenticated Graph API client
        top: Maximum number of results
        
    Returns:
        list[dict]: List of trending files or empty list on error
    """
    try:
        trending = await _graph_call(client.me.insights.trending.get(), "Graph API call")
        results = []
        if trending and trending.value:
            for item in trending.value[:top]:
                resource = item.resource_reference
                results.append({
                    "id": item.id,
                    "web_url": resource.web_url if resource else None,
                    "type": resource.type if resource else None,
                })
        return results
    except Exception as e:
        logger.error(f"Failed to get trending files: {e}")
        return [{"error": f"Failed to get trending files: {str(e)}"}]


# OneNote

async def get_onenote_notebooks(client: GraphServiceClient) -> list[dict]:
    """
    Get the user's OneNote notebooks and their sections.
    
    Args:
        client: Authenticated Graph API client
        
    Returns:
        list[dict]: List of notebooks with sections or empty list on error
    """
    try:
        cache_key = "read:onenote_notebooks"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        notebooks = await _graph_call(client.me.onenote.notebooks.get(), "Graph API call")
        results = []
        if notebooks and notebooks.value:
            for nb in notebooks.value:
                nb_info = {
                    "id": nb.id,
                    "name": nb.display_name,
                    "last_modified": str(nb.last_modified_date_time) if nb.last_modified_date_time else None,
                    "sections": [],
                }
                if nb.id:
                    sections = await _graph_call(client.me.onenote.notebooks.by_notebook_id(nb.id).sections.get(), "Graph API call")
                    if sections and sections.value:
                        for s in sections.value:
                            nb_info["sections"].append({
                                "id": s.id,
                                "name": s.display_name,
                            })
                results.append(nb_info)
        return _cache_set(cache_key, results)
    except Exception as e:
        logger.error(f"Failed to get onenote notebooks: {e}")
        return [{"error": f"Failed to get onenote notebooks: {str(e)}"}]


async def get_onenote_pages(client: GraphServiceClient, section_id: str, top: int = 25) -> list[dict]:
    """
    Get pages from a specific OneNote section.
    
    Args:
        client: Authenticated Graph API client
        section_id: The ID of the OneNote section
        top: Maximum number of pages to return
        
    Returns:
        list[dict]: List of pages or empty list on error
    """
    try:
        query_params = PagesRequestBuilder.PagesRequestBuilderGetQueryParameters(
            top=top,
        )
        request_config = RequestConfiguration[PagesRequestBuilder.PagesRequestBuilderGetQueryParameters](
            query_parameters=query_params,
        )
        pages = await _graph_call(client.me.onenote.sections.by_onenote_section_id(section_id).pages.get(request_configuration=request_config), "Graph API call")
        results = []
        if pages and pages.value:
            for page in pages.value:
                results.append({
                    "id": page.id,
                    "title": page.title,
                    "created": str(page.created_date_time) if page.created_date_time else None,
                    "last_modified": str(page.last_modified_date_time) if page.last_modified_date_time else None,
                    "web_url": page.links.one_note_web_url.href if page.links and page.links.one_note_web_url else None,
                })
        return results
    except Exception as e:
        logger.error(f"Failed to get onenote pages: {e}")
        return [{"error": f"Failed to get onenote pages: {str(e)}"}]


async def get_onenote_page_content(client: GraphServiceClient, page_id: str) -> dict:
    """
    Get rendered HTML content for a OneNote page.

    Args:
        client: Authenticated Graph API client
        page_id: OneNote page ID

    Returns:
        dict: Page metadata/content or error
    """
    try:
        page = await _graph_call(client.me.onenote.pages.by_onenote_page_id(page_id).get(), "Graph API call")
        content_bytes = await _graph_call(client.me.onenote.pages.by_onenote_page_id(page_id).content.get(), "Graph API call")

        return {
            "page_id": page_id,
            "title": page.title if page else None,
            "content_html": content_bytes.decode("utf-8", errors="replace") if content_bytes else None,
        }
    except Exception as e:
        logger.error(f"Failed to get onenote page content: {e}")
        return {"error": f"Failed to get onenote page content: {str(e)}"}


async def create_onenote_page(client: GraphServiceClient, section_id: str, title: str, content_html: str) -> dict:
    """
    Create a OneNote page in a given section.

    Args:
        client: Authenticated Graph API client
        section_id: OneNote section ID
        title: Page title
        content_html: Page HTML content

    Returns:
        dict: Create status and created page metadata or error
    """
    try:
        page = OnenotePage()
        page.title = title
        page.content = content_html

        created = await _graph_call(client.me.onenote.sections.by_onenote_section_id(section_id).pages.post(page), "Graph API call")
        if not created:
            return {"error": "Failed to create onenote page."}

        _cache_invalidate("read:onenote_notebooks")

        web_url = created.links.one_note_web_url.href if created.links and created.links.one_note_web_url else None

        return {
            "status": "created",
            "page": {
                "id": created.id,
                "title": created.title,
                "web_url": web_url,
            },
        }
    except Exception as e:
        logger.error(f"Failed to create onenote page: {e}")
        return {"error": f"Failed to create onenote page: {str(e)}"}


# Composite Assistant Tools

async def get_daily_briefing(
    client: GraphServiceClient,
    date_value: str | None = None,
    timezone_name: str = "UTC",
) -> dict:
    """
    Build a compact daily briefing for agent workflows.

    Args:
        client: Authenticated Graph API client
        date_value: Target date in YYYY-MM-DD format, default today in timezone_name
        timezone_name: IANA timezone name

    Returns:
        dict: Daily briefing payload or error
    """
    try:
        target_zone = ZoneInfo(timezone_name)
        today_local = datetime.now(target_zone).date()
        target_date = date.fromisoformat(date_value) if date_value else today_local

        days_ahead = max(1, (target_date - today_local).days + 1)

        events_raw = await get_calendar_events(client, days=days_ahead)
        upcoming_events = []
        for event in events_raw:
            start_value = event.get("start")
            if not start_value:
                continue
            try:
                start_dt = datetime.fromisoformat(start_value.replace("Z", "+00:00")).astimezone(target_zone)
            except ValueError:
                continue
            if start_dt.date() == target_date:
                upcoming_events.append(event)

        messages = await get_messages(client, top=50)
        unread_messages = [msg for msg in messages if isinstance(msg, dict) and msg.get("is_read") is False]

        tasks = await get_todo_tasks(client)
        due_today = []
        overdue = []
        for task in tasks:
            due_value = task.get("due")
            if not due_value:
                continue
            try:
                due_dt = datetime.fromisoformat(due_value.replace("Z", "+00:00")).astimezone(target_zone)
            except ValueError:
                continue
            if due_dt.date() == target_date:
                due_today.append(task)
            if due_dt.date() < target_date and task.get("status") != TodoStatus.COMPLETED.value:
                overdue.append(task)

        recent_files = await get_recent_files(client, top=5)
        relevant_people = await get_relevant_people(client, top=5)

        return {
            "date": target_date.isoformat(),
            "timezone": timezone_name,
            "calendar": {
                "upcoming_events": upcoming_events[:10],
            },
            "mail": {
                "unread_count": len(unread_messages),
                "priority_messages": unread_messages[:5],
            },
            "tasks": {
                "due_today": due_today[:10],
                "overdue": overdue[:10],
            },
            "files": {
                "recent": recent_files[:5],
            },
            "people": {
                "relevant_contacts": relevant_people[:5],
            },
        }
    except Exception as e:
        logger.error(f"Failed to build daily briefing: {e}")
        return {"error": f"Failed to build daily briefing: {str(e)}"}


async def prepare_meeting_brief(
    client: GraphServiceClient,
    event_id: str,
    include_recent_threads: bool = True,
) -> dict:
    """
    Build pre-meeting context bundle for a calendar event.

    Args:
        client: Authenticated Graph API client
        event_id: Calendar event ID
        include_recent_threads: Whether to include recent related messages

    Returns:
        dict: Meeting brief payload or error
    """
    try:
        event = await _graph_call(client.me.events.by_event_id(event_id).get(), "Graph API call")
        if not event:
            return {"error": "Event not found."}

        attendees = []
        attendee_emails = set()
        for attendee in event.attendees or []:
            email = attendee.email_address.address if attendee.email_address else None
            if email:
                attendee_emails.add(email.lower())
                attendees.append(email)

        people_candidates = await get_relevant_people(client, top=100)
        attendee_context = []
        for person in people_candidates:
            person_emails = [email.lower() for email in person.get("emails", []) if isinstance(email, str)]
            if attendee_emails.intersection(person_emails):
                attendee_context.append(person)

        subject = event.subject or ""
        related_messages = []
        if include_recent_threads and subject:
            message_results = await search_messages(client, query=subject, top=10)
            if message_results and not message_results[0].get("error"):
                related_messages = message_results

        related_files = []
        if subject:
            file_results = await search_files(client, query=subject, top=5)
            if file_results and not file_results[0].get("error"):
                related_files = file_results

        prep_notes = [
            f"Review agenda for '{subject}'." if subject else "Review event details.",
            f"You have {len(attendees)} attendee(s) for this meeting.",
            f"Found {len(related_messages)} related recent message(s).",
            f"Found {len(related_files)} related file(s).",
        ]

        return {
            "event": {
                "id": event.id,
                "subject": event.subject,
                "start": event.start.date_time if event.start else None,
                "end": event.end.date_time if event.end else None,
                "attendees": attendees,
            },
            "attendee_context": attendee_context[:20],
            "related_messages": related_messages,
            "related_files": related_files,
            "prep_notes": prep_notes,
        }
    except Exception as e:
        logger.error(f"Failed to prepare meeting brief: {e}")
        return {"error": f"Failed to prepare meeting brief: {str(e)}"}


# Operability

async def health_check(client: GraphServiceClient) -> dict:
    """
    Verify Graph connectivity and authentication viability.

    Args:
        client: Authenticated Graph API client

    Returns:
        dict: Health check status and details
    """
    checked_at = datetime.now(timezone.utc).isoformat()
    try:
        profile = await _graph_call(client.me.get(), "Graph API call")
        details = ["Successfully queried Microsoft Graph /me endpoint."]
        if profile and profile.id:
            details.append(f"Authenticated user id: {profile.id}")

        return {
            "status": "ok",
            "graph_reachable": True,
            "auth_valid": True,
            "checked_at": checked_at,
            "details": details,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "graph_reachable": False,
            "auth_valid": False,
            "checked_at": checked_at,
            "details": [str(e)],
        }
