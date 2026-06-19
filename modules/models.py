"""
Pydantic validation models for MCP tool inputs.

Provides standardized input validation schemas for all MCP tools,
ensuring type safety and consistent error messages.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from modules.enums import CONTENT_TYPE_VALUES, TODO_STATUS_VALUES, EVENT_RESPONSE_VALUES


CONTENT_TYPE_PATTERN = f"^({'|'.join(CONTENT_TYPE_VALUES)})$"
TODO_STATUS_PATTERN = f"^({'|'.join(TODO_STATUS_VALUES)})$"
EVENT_RESPONSE_PATTERN = f"^({'|'.join(EVENT_RESPONSE_VALUES)})$"


# Email/Message Operations

class ReplyToMessageInput(BaseModel):
    """Validation schema for reply_to_message tool."""
    model_config = ConfigDict(str_strip_whitespace=True)

    message_id: str = Field(..., min_length=1, description="Message ID to reply to")
    body: str = Field(..., min_length=1, description="Reply body text")
    content_type: str = Field(default="text", pattern=CONTENT_TYPE_PATTERN, description="text or html")
    reply_all: bool = Field(default=False, description="Reply to all recipients")
    mailbox: Optional[str] = Field(default=None, description="Optional shared mailbox")
    
    @field_validator('body')
    @classmethod
    def body_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Reply body cannot be empty")
        return v.strip()


class ForwardMessageInput(BaseModel):
    """Validation schema for forward_message tool."""
    model_config = ConfigDict(str_strip_whitespace=True)

    message_id: str = Field(..., min_length=1, description="Message ID to forward")
    to: List[str] = Field(..., min_length=1, description="Recipient email addresses")
    comment: Optional[str] = Field(default=None, description="Optional forwarding comment")
    mailbox: Optional[str] = Field(default=None, description="Optional shared mailbox")
    
    @field_validator('to')
    @classmethod
    def validate_recipients(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one recipient required")
        for email in v:
            if not email or not email.strip():
                raise ValueError("Recipient email addresses cannot be empty")
        return [e.strip() for e in v]


class MarkMessageReadInput(BaseModel):
    """Validation schema for mark_message_read tool."""
    model_config = ConfigDict(str_strip_whitespace=True)

    message_id: str = Field(..., min_length=1, description="Message ID")
    is_read: bool = Field(default=True, description="Read state")
    mailbox: Optional[str] = Field(default=None, description="Optional shared mailbox")


class SendMessageInput(BaseModel):
    """Validation schema for send_message tool."""
    to: List[str] = Field(..., min_length=1, description="Recipient email addresses")
    subject: str = Field(..., min_length=1, description="Message subject")
    body: str = Field(..., min_length=1, description="Message body")
    cc: List[str] = Field(default_factory=list, description="CC recipients")
    bcc: List[str] = Field(default_factory=list, description="BCC recipients")
    content_type: str = Field(default="text", pattern=CONTENT_TYPE_PATTERN, description="text or html")
    
    @field_validator('to', 'cc', 'bcc')
    @classmethod
    def validate_email_lists(cls, v):
        if not v:
            return v
        for email in v:
            if not email or not email.strip():
                raise ValueError("Email addresses cannot be empty")
        return [e.strip() for e in v]


# Task Operations

class CreateTodoTaskInput(BaseModel):
    """Validation schema for create_todo_task tool."""
    list_id: str = Field(..., min_length=1, description="Todo list ID")
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    due_date: Optional[str] = Field(default=None, description="Due date (YYYY-MM-DD)")
    
    @field_validator('due_date')
    @classmethod
    def validate_date_format(cls, v):
        if v is None:
            return v
        try:
            # Simple format validation
            import datetime
            datetime.datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Due date must be in YYYY-MM-DD format")
        return v


class UpdateTodoTaskInput(BaseModel):
    """Validation schema for update_todo_task tool."""
    list_id: str = Field(..., min_length=1, description="Todo list ID")
    task_id: str = Field(..., min_length=1, description="Task ID")
    title: Optional[str] = Field(default=None, max_length=255, description="New title")
    due_date: Optional[str] = Field(default=None, description="New due date")
    status: Optional[str] = Field(default=None, pattern=TODO_STATUS_PATTERN, description="Task status")
    
    @field_validator('due_date')
    @classmethod
    def validate_date_format(cls, v):
        if v is None:
            return v
        try:
            import datetime
            datetime.datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Due date must be in YYYY-MM-DD format")
        return v


class DeleteTodoTaskInput(BaseModel):
    """Validation schema for delete_todo_task tool."""
    list_id: str = Field(..., min_length=1, description="Todo list ID")
    task_id: str = Field(..., min_length=1, description="Task ID to delete")


# Calendar Operations

class CreateCalendarEventInput(BaseModel):
    """Validation schema for create_calendar_event tool."""
    subject: str = Field(..., min_length=1, description="Event subject")
    start: str = Field(..., description="Start datetime (ISO 8601)")
    end: str = Field(..., description="End datetime (ISO 8601)")
    attendees: List[str] = Field(default_factory=list, description="Attendee email addresses")
    location: Optional[str] = Field(default=None, description="Event location")
    body: Optional[str] = Field(default=None, description="Event description")
    
    @field_validator('attendees')
    @classmethod
    def validate_attendees(cls, v):
        if not v:
            return v
        for email in v:
            if not email or not email.strip():
                raise ValueError("Attendee email addresses cannot be empty")
        return [e.strip() for e in v]


class RespondToEventInput(BaseModel):
    """Validation schema for respond_to_event tool."""
    event_id: str = Field(..., min_length=1, description="Event ID")
    response: str = Field(..., pattern=EVENT_RESPONSE_PATTERN, description="Response: accept, decline, or tentative")
    comment: Optional[str] = Field(default=None, description="Optional response comment")


# General/Utility Operations

class SearchMessagesInput(BaseModel):
    """Validation schema for search_messages tool."""
    query: str = Field(..., min_length=1, description="KQL search query")
    limit: int = Field(default=10, ge=1, le=100, description="Max results (1-100)")


class MoveMessageInput(BaseModel):
    """Validation schema for move_message tool."""
    message_id: str = Field(..., min_length=1, description="Message ID")
    destination_id: str = Field(..., min_length=1, description="Destination folder ID")
    mailbox: Optional[str] = Field(default=None, description="Optional shared mailbox")


class GetMessagesInput(BaseModel):
    """Validation schema for get_messages tool."""
    mailbox: Optional[str] = Field(default=None, description="Optional shared mailbox")
    limit: int = Field(default=10, ge=1, le=100, description="Max messages to return (1-100)")


class SendChatMessageInput(BaseModel):
    """Validation schema for send_chat_message tool."""
    chat_id: str = Field(..., min_length=1, description="Chat ID")
    body: str = Field(..., min_length=1, description="Message body")
    content_type: str = Field(default="text", pattern=CONTENT_TYPE_PATTERN, description="text or html")
