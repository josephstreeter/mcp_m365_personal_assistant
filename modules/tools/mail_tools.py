"""Mail MCP tool wrappers."""

from __future__ import annotations

import json
from typing import Any, Callable

from pydantic import ValidationError as PydanticValidationError

from modules.enums import ContentType
from modules.models import ReplyToMessageInput, ForwardMessageInput, MarkMessageReadInput


def register_mail_tools(
    *,
    mcp: Any,
    get_singleton_client: Callable[[], Any],
    personal_assistant_provider: Callable[[], Any],
    error_payload: Callable[..., str],
):
    @mcp.tool()
    async def get_messages(top: int = 25, mailbox: str | None = None) -> str:
        """Get the user's most recent Exchange Online email messages.

        Example:
            >>> await get_messages(top=10)
        """
        if top < 1 or top > 200:
            return error_payload("top must be between 1 and 200.")

        client = get_singleton_client()
        results = await personal_assistant_provider().get_messages(client, top=top, mailbox=mailbox)
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    async def send_message(
        to: str,
        subject: str,
        body: str,
        content_type: str = ContentType.TEXT.value,
        from_address: str | None = None,
    ) -> str:
        """Send an email message.

        Example:
            >>> await send_message(to=\"alex@contoso.com\", subject=\"Weekly update\", body=\"Status...\")
        """
        if not to.strip():
            return error_payload("to is required.")
        if not subject.strip():
            return error_payload("subject is required.")
        if not body.strip():
            return error_payload("body is required.")
        normalized_content_type = content_type.strip().lower()
        if normalized_content_type not in {item.value for item in ContentType}:
            return error_payload("content_type must be one of: text, html.")

        client = get_singleton_client()
        result = await personal_assistant_provider().send_message(
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
            return error_payload("query is required.")
        if top < 1 or top > 200:
            return error_payload("top must be between 1 and 200.")

        client = get_singleton_client()
        results = await personal_assistant_provider().search_messages(client, query=query, top=top, mailbox=mailbox)
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    async def get_message_by_id(message_id: str, mailbox: str | None = None) -> str:
        """Retrieve a single Exchange Online email message by its Graph API message ID."""
        if not message_id.strip():
            return error_payload("message_id is required.")

        client = get_singleton_client()
        result = await personal_assistant_provider().get_message_by_id(client, message_id=message_id, mailbox=mailbox)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def reply_to_message(
        message_id: str,
        body: str,
        content_type: str = ContentType.TEXT.value,
        reply_all: bool = False,
        mailbox: str | None = None,
    ) -> str:
        """Reply to an existing Exchange Online email message."""
        try:
            validated = ReplyToMessageInput(
                message_id=message_id,
                body=body,
                content_type=content_type,
                reply_all=reply_all,
                mailbox=mailbox,
            )
        except PydanticValidationError as e:
            errors = e.errors()
            if any(err.get("loc") == ("message_id",) for err in errors):
                return error_payload("message_id is required.")
            if any(err.get("loc") == ("content_type",) for err in errors):
                return error_payload("content_type must be one of: text, html.")
            if any(err.get("loc") == ("body",) for err in errors):
                return error_payload("body is required.")
            error_messages = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in errors])
            return error_payload(error_messages)

        client = get_singleton_client()
        result = await personal_assistant_provider().reply_to_message(
            client,
            message_id=validated.message_id,
            body=validated.body,
            content_type=validated.content_type,
            reply_all=validated.reply_all,
            mailbox=validated.mailbox,
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
        try:
            validated = ForwardMessageInput(
                message_id=message_id,
                to=to,
                comment=comment,
                mailbox=mailbox,
            )
        except PydanticValidationError as e:
            errors = e.errors()
            if any(err.get("loc") == ("message_id",) for err in errors):
                return error_payload("message_id is required.")
            if any(err.get("loc") == ("to",) for err in errors):
                msg = str(errors[0].get("msg", "")).lower()
                if "at least" in msg or "list should have" in msg:
                    return error_payload("to must be a non-empty list of email addresses.")
                return error_payload("to must contain non-empty email addresses.")
            if any(err.get("loc") == ("comment",) for err in errors):
                return error_payload("comment must be a string when provided.")
            error_messages = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in errors])
            return error_payload(error_messages)

        client = get_singleton_client()
        result = await personal_assistant_provider().forward_message(
            client,
            message_id=validated.message_id,
            to=validated.to,
            comment=validated.comment,
            mailbox=validated.mailbox,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def mark_message_read(message_id: str, is_read: bool = True, mailbox: str | None = None) -> str:
        """Mark an Exchange Online email message as read or unread."""
        try:
            validated = MarkMessageReadInput(message_id=message_id, is_read=is_read, mailbox=mailbox)
        except PydanticValidationError as e:
            errors = e.errors()
            if any(err.get("loc") == ("message_id",) for err in errors):
                return error_payload("message_id is required.")
            error_messages = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in errors])
            return error_payload(error_messages)

        client = get_singleton_client()
        result = await personal_assistant_provider().mark_message_read(
            client,
            message_id=validated.message_id,
            is_read=validated.is_read,
            mailbox=validated.mailbox,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def list_mail_folders(top: int = 100, mailbox: str | None = None) -> str:
        """List mail folders and their IDs for the current or shared mailbox."""
        if top < 1 or top > 200:
            return error_payload("top must be between 1 and 200.")

        client = get_singleton_client()
        results = await personal_assistant_provider().list_mail_folders(client, top=top, mailbox=mailbox)
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    async def move_message(message_id: str, destination_folder_id: str, mailbox: str | None = None) -> str:
        """Move an Exchange Online email message to a destination folder."""
        if not message_id.strip():
            return error_payload("message_id is required.")
        if not destination_folder_id.strip():
            return error_payload("destination_folder_id is required.")

        client = get_singleton_client()
        result = await personal_assistant_provider().move_message(
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
            return error_payload("message_id is required.")

        client = get_singleton_client()
        result = await personal_assistant_provider().get_message_attachments(client, message_id=message_id, mailbox=mailbox)
        return json.dumps(result, indent=2, default=str)

    return {
        "get_messages": get_messages,
        "send_message": send_message,
        "search_messages": search_messages,
        "get_message_by_id": get_message_by_id,
        "reply_to_message": reply_to_message,
        "forward_message": forward_message,
        "mark_message_read": mark_message_read,
        "list_mail_folders": list_mail_folders,
        "move_message": move_message,
        "get_message_attachments": get_message_attachments,
    }
