"""
Personal productivity functions for Microsoft 365 (M365) integration.
Handles user profile, email, calendar, tasks, contacts, files, Teams, and insights.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.graph_service_client import GraphServiceClient
from msgraph.generated.models.todo_task import TodoTask
from msgraph.generated.models.task_status import TaskStatus
from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone
from msgraph.generated.models.message import Message
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.models.event import Event
from msgraph.generated.models.location import Location
from msgraph.generated.models.attendee import Attendee
from msgraph.generated.models.attendee_type import AttendeeType
from msgraph.generated.models.chat import Chat
from msgraph.generated.models.chat_type import ChatType
from msgraph.generated.models.chat_message import ChatMessage
from msgraph.generated.models.aad_user_conversation_member import AadUserConversationMember
from msgraph.generated.models.conversation_member import ConversationMember
from msgraph.generated.users.item.messages.messages_request_builder import MessagesRequestBuilder
from msgraph.generated.users.item.messages.item.message_item_request_builder import MessageItemRequestBuilder
from msgraph.generated.users.item.calendar_view.calendar_view_request_builder import CalendarViewRequestBuilder
from msgraph.generated.users.item.contacts.contacts_request_builder import ContactsRequestBuilder
from msgraph.generated.users.item.chats.chats_request_builder import ChatsRequestBuilder
from msgraph.generated.users.item.chats.item.messages.messages_request_builder import MessagesRequestBuilder as ChatMessagesRequestBuilder
from msgraph.generated.users.item.people.people_request_builder import PeopleRequestBuilder
from msgraph.generated.users.item.onenote.sections.item.pages.pages_request_builder import PagesRequestBuilder
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import SendMailPostRequestBody
from msgraph.generated.communications.get_presences_by_user_id.get_presences_by_user_id_post_request_body import GetPresencesByUserIdPostRequestBody

logger = logging.getLogger(__name__)


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
        profile = await client.me.get()
        if profile:
            return {
                "display_name": profile.display_name,
                "email": profile.mail,
                "job_title": profile.job_title,
                "id": profile.id,
            }
        return {"error": "Could not retrieve user profile."}
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        return {"error": f"Failed to get user profile: {str(e)}"}


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
        task_lists = await client.me.todo.lists.get()
        if task_lists and task_lists.value:
            for task_list in task_lists.value:
                list_name = task_list.display_name
                if not task_list.id:
                    continue
                tasks = await client.me.todo.lists.by_todo_task_list_id(task_list.id).tasks.get()
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
        task_lists = await client.me.todo.lists.get()
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

        created = await client.me.todo.lists.by_todo_task_list_id(target_list.id).tasks.post(new_task)
        if created:
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
        task_lists = await client.me.todo.lists.get()
        target_list = None
        if task_lists and task_lists.value:
            for tl in task_lists.value:
                if tl.display_name and tl.display_name.lower() == list_name.lower():
                    target_list = tl
                    break
        
        if not target_list or not target_list.id:
            return {"error": f"Task list '{list_name}' not found."}

        tasks = await client.me.todo.lists.by_todo_task_list_id(target_list.id).tasks.get()
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
        updated = await client.me.todo.lists.by_todo_task_list_id(target_list.id).tasks.by_todo_task_id(target_task.id).patch(update)
        if updated:
            return {"title": updated.title, "status": updated.status.value if updated.status else "unknown"}
        return {"error": "Failed to update task."}
    except Exception as e:
        logger.error(f"Failed to complete todo task: {e}")
        return {"error": f"Failed to complete task: {str(e)}"}


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
            messages = await client.users.by_user_id(mailbox).messages.get(request_configuration=request_config)
        else:
            messages = await client.me.messages.get(request_configuration=request_config)
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
        body_type = BodyType.Html if content_type.lower() == "html" else BodyType.Text
        msg.body = ItemBody(content=body, content_type=body_type)
        
        recipient = Recipient(email_address=EmailAddress(address=to))
        msg.to_recipients = [recipient]
        
        # Set from address if specified (requires appropriate permissions)
        if from_address:
            msg.from_ = Recipient(email_address=EmailAddress(address=from_address))

        request_body = SendMailPostRequestBody()
        request_body.message = msg
        request_body.save_to_sent_items = True
        await client.me.send_mail.post(request_body)
        return {"status": "sent", "to": to, "subject": subject, "content_type": content_type, "from": from_address or "authenticated user"}
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
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
            messages = await client.users.by_user_id(mailbox).messages.get(request_configuration=request_config)
        else:
            messages = await client.me.messages.get(request_configuration=request_config)
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
            msg = await client.users.by_user_id(mailbox).messages.by_message_id(message_id).get(request_configuration=request_config)
        else:
            msg = await client.me.messages.by_message_id(message_id).get(request_configuration=request_config)

        if not msg:
            return {"error": "Message not found."}

        # Extract body type and content
        body_type = "html" if msg.body and msg.body.content_type == BodyType.Html else "text"
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
        events = await client.me.calendar_view.get(request_configuration=request_config)
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
        return results
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

        created = await client.me.events.post(event)
        if created:
            return {
                "id": created.id,
                "subject": created.subject,
                "start": created.start.date_time if created.start else None,
                "end": created.end.date_time if created.end else None,
            }
        return {"error": "Failed to create event."}
    except Exception as e:
        logger.error(f"Failed to create calendar event: {e}")
        return {"error": f"Failed to create event: {str(e)}"}


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
        query_params = ContactsRequestBuilder.ContactsRequestBuilderGetQueryParameters(
            select=["displayName", "emailAddresses", "mobilePhone", "businessPhones", "companyName", "jobTitle"],
            top=top,
        )
        request_config = RequestConfiguration[ContactsRequestBuilder.ContactsRequestBuilderGetQueryParameters](
            query_parameters=query_params,
        )
        contacts = await client.me.contacts.get(request_configuration=request_config)
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
        return results
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
        drive = await client.me.drive.get()
        if not drive or not drive.id:
            return [{"error": "Could not access user's drive."}]

        children_builder = getattr(client.drives.by_drive_id(drive.id).root, "children")
        children_resp = await children_builder.get()
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
        return results
    except Exception as e:
        logger.error(f"Failed to get recent files: {e}")
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
        drive = await client.me.drive.get()
        if not drive or not drive.id:
            return [{"error": "Could not access user's drive."}]

        search_results = await client.drives.by_drive_id(drive.id).search_with_q(q=query).get()
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
        chats = await client.me.chats.get(request_configuration=request_config)
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
        messages = await client.me.chats.by_chat_id(chat_id).messages.get(request_configuration=request_config)
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
            me = await client.me.get()
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
            
            created_chat = await client.chats.post(chat)
            
            if not created_chat or not created_chat.id:
                return {"error": "Failed to create or retrieve chat"}
            
            target_chat_id = created_chat.id
            target = recipient
        
        # Send message to the chat
        body_type = BodyType.Html if content_type.lower() == "html" else BodyType.Text
        chat_message = ChatMessage()
        chat_message.body = ItemBody(
            content_type=body_type,
            content=message
        )
        
        await client.chats.by_chat_id(target_chat_id).messages.post(chat_message)
        
        return {
            "status": "sent",
            "to": target,
            "chat_id": target_chat_id,
            "content_type": content_type
        }
    except Exception as e:
        logger.error(f"Failed to send chat message: {e}")
        return {"error": f"Failed to send chat message: {str(e)}"}


async def get_teams_and_channels(client: GraphServiceClient) -> list[dict]:
    """
    List the user's joined Teams and their channels.
    
    Args:
        client: Authenticated Graph API client
        
    Returns:
        list[dict]: List of teams with their channels or empty list on error
    """
    try:
        teams = await client.me.joined_teams.get()
        results = []
        if teams and teams.value:
            for team in teams.value:
                team_info = {
                    "team_id": team.id,
                    "team_name": team.display_name,
                    "channels": [],
                }
                if team.id:
                    channels = await client.teams.by_team_id(team.id).channels.get()
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
            presences = await client.communications.get_presences_by_user_id.post(request_body)
            if presences and presences.value:
                for p in presences.value:
                    results.append({
                        "user_id": p.id,
                        "availability": p.availability,
                        "activity": p.activity,
                    })
        else:
            presence = await client.me.presence.get()
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
        query_params = PeopleRequestBuilder.PeopleRequestBuilderGetQueryParameters(
            top=top,
        )
        request_config = RequestConfiguration[PeopleRequestBuilder.PeopleRequestBuilderGetQueryParameters](
            query_parameters=query_params,
        )
        people = await client.me.people.get(request_configuration=request_config)
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
        return results
    except Exception as e:
        logger.error(f"Failed to get relevant people: {e}")
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
        trending = await client.me.insights.trending.get()
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
        notebooks = await client.me.onenote.notebooks.get()
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
                    sections = await client.me.onenote.notebooks.by_notebook_id(nb.id).sections.get()
                    if sections and sections.value:
                        for s in sections.value:
                            nb_info["sections"].append({
                                "id": s.id,
                                "name": s.display_name,
                            })
                results.append(nb_info)
        return results
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
        pages = await client.me.onenote.sections.by_onenote_section_id(section_id).pages.get(request_configuration=request_config)
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
