import asyncio
import importlib
import json
import pathlib
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


@pytest.fixture
def configured_main(monkeypatch):
    monkeypatch.setenv("client_id", "test-client-id")
    monkeypatch.setenv("tenant_id", "test-tenant-id")

    module = importlib.import_module("main")
    monkeypatch.setattr(module, "get_singleton_client", lambda: object())
    return module


def test_reply_to_message_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def reply_to_message(self, _client, **kwargs):
            return {"status": "sent", **kwargs}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(
        module.reply_to_message(
            message_id="m1",
            body="hello",
            content_type="text",
            reply_all=True,
            mailbox="shared@example.com",
        )
    )
    data = json.loads(payload)

    assert data["status"] == "sent"
    assert data["message_id"] == "m1"
    assert data["reply_all"] is True
    assert data["mailbox"] == "shared@example.com"


def test_forward_message_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def forward_message(self, _client, **kwargs):
            return {"status": "sent", **kwargs}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(
        module.forward_message(
            message_id="m1",
            to=["recipient1@example.com", "recipient2@example.com"],
            comment="FYI",
            mailbox="shared@example.com",
        )
    )
    data = json.loads(payload)

    assert data["status"] == "sent"
    assert data["message_id"] == "m1"
    assert data["to"] == ["recipient1@example.com", "recipient2@example.com"]
    assert data["mailbox"] == "shared@example.com"


def test_forward_message_wrapper_no_comment(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def forward_message(self, _client, **kwargs):
            return {"status": "sent", **kwargs}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(
        module.forward_message(
            message_id="m2",
            to=["recipient@example.com"],
        )
    )
    data = json.loads(payload)

    assert data["status"] == "sent"
    assert data["message_id"] == "m2"
    assert data["to"] == ["recipient@example.com"]


def test_forward_message_wrapper_rejects_empty_message_id(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def forward_message(self, _client, **kwargs):
            raise AssertionError("forward_message helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.forward_message(message_id="   ", to=["recipient@example.com"]))
    data = json.loads(payload)

    assert "error" in data
    assert "message_id is required" in data["error"].lower()


def test_forward_message_wrapper_rejects_empty_recipients_list(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def forward_message(self, _client, **kwargs):
            raise AssertionError("forward_message helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.forward_message(message_id="m1", to=[]))
    data = json.loads(payload)

    assert "error" in data
    assert "non-empty list" in data["error"].lower()


def test_forward_message_wrapper_rejects_empty_recipient_emails(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def forward_message(self, _client, **kwargs):
            raise AssertionError("forward_message helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.forward_message(message_id="m1", to=["recipient@example.com", "   "]))
    data = json.loads(payload)

    assert "error" in data
    assert "non-empty email addresses" in data["error"].lower()


def test_mark_message_read_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def mark_message_read(self, _client, **kwargs):
            return {"status": "updated", **kwargs}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.mark_message_read(message_id="m2", is_read=False, mailbox=None))
    data = json.loads(payload)

    assert data["status"] == "updated"
    assert data["message_id"] == "m2"
    assert data["is_read"] is False


def test_list_mail_folders_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def list_mail_folders(self, _client, **kwargs):
            return [{"id": "inbox", "display_name": "Inbox", **kwargs}]

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.list_mail_folders(top=50, mailbox="shared@example.com"))
    data = json.loads(payload)

    assert data[0]["id"] == "inbox"
    assert data[0]["top"] == 50
    assert data[0]["mailbox"] == "shared@example.com"


def test_move_message_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def move_message(self, _client, **kwargs):
            return {"status": "moved", **kwargs}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.move_message(message_id="m3", destination_folder_id="archive-id", mailbox=None))
    data = json.loads(payload)

    assert data["status"] == "moved"
    assert data["message_id"] == "m3"
    assert data["destination_folder_id"] == "archive-id"


def test_get_message_attachments_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def get_message_attachments(self, _client, **kwargs):
            return {"message_id": kwargs["message_id"], "attachments": [{"id": "a1"}]}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.get_message_attachments(message_id="m4", mailbox="shared@example.com"))
    data = json.loads(payload)

    assert data["message_id"] == "m4"
    assert data["attachments"][0]["id"] == "a1"


def test_reply_to_message_helper_empty_body_returns_error():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    client = MagicMock()
    result = asyncio.run(
        personal_assistant.reply_to_message(
            client,
            message_id="m1",
            body="   ",
            content_type="text",
            reply_all=False,
            mailbox=None,
        )
    )

    assert "error" in result
    assert "cannot be empty" in result["error"].lower()


def test_forward_message_helper_forwards_to_recipients():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    forward_endpoint = MagicMock()
    forward_endpoint.post = AsyncMock(return_value=None)

    target = MagicMock()
    target.forward = forward_endpoint

    client = MagicMock()
    client.me.messages.by_message_id.return_value = target

    result = asyncio.run(
        personal_assistant.forward_message(
            client,
            message_id="m1",
            to=["recipient1@example.com", "recipient2@example.com"],
            comment="FYI",
            mailbox=None,
        )
    )

    assert result["status"] == "sent"
    assert result["message_id"] == "m1"
    assert result["to"] == ["recipient1@example.com", "recipient2@example.com"]
    forward_endpoint.post.assert_awaited_once()

    call_arg = forward_endpoint.post.call_args[0][0]
    assert len(call_arg.to_recipients) == 2
    assert call_arg.to_recipients[0].email_address.address == "recipient1@example.com"
    assert call_arg.to_recipients[1].email_address.address == "recipient2@example.com"
    assert call_arg.comment == "FYI"


def test_forward_message_helper_handles_forward_error():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    forward_endpoint = MagicMock()
    forward_endpoint.post = AsyncMock(side_effect=Exception("Graph API error"))

    target = MagicMock()
    target.forward = forward_endpoint

    client = MagicMock()
    client.me.messages.by_message_id.return_value = target

    result = asyncio.run(
        personal_assistant.forward_message(
            client,
            message_id="m1",
            to=["recipient@example.com"],
            comment=None,
            mailbox=None,
        )
    )

    assert "error" in result
    assert "graph api error" in result["error"].lower()
    assert result.get("error_type") == "GraphAPIError"



def test_mark_message_read_helper_updates_message():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    target = MagicMock()
    target.patch = AsyncMock(return_value=SimpleNamespace(id="m2", is_read=True))

    client = MagicMock()
    client.me.messages.by_message_id.return_value = target

    result = asyncio.run(personal_assistant.mark_message_read(client, message_id="m2", is_read=True, mailbox=None))

    assert result["status"] == "updated"
    assert result["message_id"] == "m2"
    assert result["is_read"] is True
    target.patch.assert_awaited_once()


def test_list_mail_folders_helper_clamps_top_to_200():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    folders_response = SimpleNamespace(
        value=[
            SimpleNamespace(id="inbox", display_name="Inbox", total_item_count=10, unread_item_count=2),
        ]
    )

    client = MagicMock()
    client.me.mail_folders.get = AsyncMock(return_value=folders_response)

    result = asyncio.run(personal_assistant.list_mail_folders(client, top=500, mailbox=None))

    assert result[0]["id"] == "inbox"
    assert result[0]["display_name"] == "Inbox"

    call_kwargs = client.me.mail_folders.get.await_args.kwargs
    request_config = call_kwargs["request_configuration"]
    assert request_config.query_parameters.top == 200


def test_move_message_helper_returns_destination_message_id():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    target = MagicMock()
    target.move.post = AsyncMock(return_value=SimpleNamespace(id="m3-new"))

    client = MagicMock()
    client.me.messages.by_message_id.return_value = target

    result = asyncio.run(
        personal_assistant.move_message(
            client,
            message_id="m3",
            destination_folder_id="archive-id",
            mailbox=None,
        )
    )

    assert result["status"] == "moved"
    assert result["source_message_id"] == "m3"
    assert result["destination_message_id"] == "m3-new"
    assert result["destination_folder_id"] == "archive-id"


def test_get_message_attachments_helper_shapes_metadata():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    attachments_response = SimpleNamespace(
        value=[
            SimpleNamespace(
                id="a1",
                name="report.pdf",
                content_type="application/pdf",
                size=1024,
                is_inline=False,
                odata_type="#microsoft.graph.fileAttachment",
            )
        ]
    )

    target = MagicMock()
    target.attachments.get = AsyncMock(return_value=attachments_response)

    client = MagicMock()
    client.me.messages.by_message_id.return_value = target

    result = asyncio.run(personal_assistant.get_message_attachments(client, message_id="m4", mailbox=None))

    assert result["message_id"] == "m4"
    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["id"] == "a1"
    assert result["attachments"][0]["name"] == "report.pdf"


def test_reply_to_message_wrapper_rejects_empty_message_id(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def reply_to_message(self, _client, **kwargs):
            raise AssertionError("reply_to_message helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.reply_to_message(message_id="   ", body="hello"))
    data = json.loads(payload)

    assert "error" in data
    assert "message_id is required" in data["error"].lower()


def test_reply_to_message_wrapper_rejects_invalid_content_type(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def reply_to_message(self, _client, **kwargs):
            raise AssertionError("reply_to_message helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.reply_to_message(message_id="m1", body="hello", content_type="markdown"))
    data = json.loads(payload)

    assert "error" in data
    assert "content_type must be one of" in data["error"].lower()


def test_mark_message_read_wrapper_rejects_empty_message_id(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def mark_message_read(self, _client, **kwargs):
            raise AssertionError("mark_message_read helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.mark_message_read(message_id="  "))
    data = json.loads(payload)

    assert "error" in data
    assert "message_id is required" in data["error"].lower()


def test_list_mail_folders_wrapper_rejects_invalid_top(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def list_mail_folders(self, _client, **kwargs):
            raise AssertionError("list_mail_folders helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.list_mail_folders(top=0))
    data = json.loads(payload)

    assert "error" in data
    assert "between 1 and 200" in data["error"].lower()


def test_move_message_wrapper_rejects_empty_destination_folder_id(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def move_message(self, _client, **kwargs):
            raise AssertionError("move_message helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.move_message(message_id="m3", destination_folder_id="  "))
    data = json.loads(payload)

    assert "error" in data
    assert "destination_folder_id is required" in data["error"].lower()


def test_get_message_attachments_wrapper_rejects_empty_message_id(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def get_message_attachments(self, _client, **kwargs):
            raise AssertionError("get_message_attachments helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.get_message_attachments(message_id=" "))
    data = json.loads(payload)

    assert "error" in data
    assert "message_id is required" in data["error"].lower()


def test_get_messages_wrapper_rejects_invalid_top(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def get_messages(self, _client, **kwargs):
            raise AssertionError("get_messages helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.get_messages(top=0))
    data = json.loads(payload)

    assert "error" in data
    assert "between 1 and 200" in data["error"].lower()
    assert data["error_type"] == "ValidationError"
    assert data["retryable"] is False


def test_send_message_wrapper_rejects_empty_to(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def send_message(self, _client, **kwargs):
            raise AssertionError("send_message helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.send_message(to="   ", subject="Hi", body="Hello"))
    data = json.loads(payload)

    assert "error" in data
    assert "to is required" in data["error"].lower()


def test_send_message_wrapper_rejects_invalid_content_type(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def send_message(self, _client, **kwargs):
            raise AssertionError("send_message helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.send_message(to="a@example.com", subject="Hi", body="Hello", content_type="md"))
    data = json.loads(payload)

    assert "error" in data
    assert "content_type must be one of" in data["error"].lower()


def test_search_messages_wrapper_rejects_empty_query(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def search_messages(self, _client, **kwargs):
            raise AssertionError("search_messages helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.search_messages(query="   "))
    data = json.loads(payload)

    assert "error" in data
    assert "query is required" in data["error"].lower()


def test_search_messages_wrapper_rejects_invalid_top(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def search_messages(self, _client, **kwargs):
            raise AssertionError("search_messages helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.search_messages(query="invoice", top=500))
    data = json.loads(payload)

    assert "error" in data
    assert "between 1 and 200" in data["error"].lower()


def test_get_message_by_id_wrapper_rejects_empty_message_id(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def get_message_by_id(self, _client, **kwargs):
            raise AssertionError("get_message_by_id helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.get_message_by_id(message_id="   "))
    data = json.loads(payload)

    assert "error" in data
    assert "message_id is required" in data["error"].lower()
