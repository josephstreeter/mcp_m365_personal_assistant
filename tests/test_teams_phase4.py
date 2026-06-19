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


def test_get_chat_participants_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def get_chat_participants(self, _client, **kwargs):
            return {"chat_id": kwargs["chat_id"], "participants": [{"id": "u1"}]}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.get_chat_participants(chat_id="chat-1"))
    data = json.loads(payload)

    assert data["chat_id"] == "chat-1"
    assert data["participants"][0]["id"] == "u1"


def test_send_channel_message_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def send_channel_message(self, _client, **kwargs):
            return {"status": "sent", **kwargs}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(
        module.send_channel_message(
            team_id="team-1",
            channel_id="channel-1",
            message="hello",
            content_type="HTML",
        )
    )
    data = json.loads(payload)

    assert data["status"] == "sent"
    assert data["team_id"] == "team-1"
    assert data["channel_id"] == "channel-1"
    assert data["content_type"] == "html"


def test_get_chat_participants_wrapper_rejects_empty_chat_id(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def get_chat_participants(self, _client, **kwargs):
            raise AssertionError("get_chat_participants helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.get_chat_participants(chat_id="  "))
    data = json.loads(payload)

    assert "error" in data
    assert "chat_id is required" in data["error"].lower()


def test_send_channel_message_wrapper_rejects_invalid_content_type(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def send_channel_message(self, _client, **kwargs):
            raise AssertionError("send_channel_message helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(
        module.send_channel_message(
            team_id="team-1",
            channel_id="channel-1",
            message="hello",
            content_type="markdown",
        )
    )
    data = json.loads(payload)

    assert "error" in data
    assert "content_type must be one of" in data["error"].lower()


def test_get_chat_participants_helper_shapes_members():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    members_response = SimpleNamespace(
        value=[
            SimpleNamespace(
                user_id="user-1",
                id="member-1",
                display_name="User One",
                email="user1@example.com",
                roles=["owner"],
            )
        ]
    )

    client = MagicMock()
    client.me.chats.by_chat_id.return_value.members.get = AsyncMock(return_value=members_response)

    result = asyncio.run(personal_assistant.get_chat_participants(client, chat_id="chat-1"))

    assert result["chat_id"] == "chat-1"
    assert len(result["participants"]) == 1
    assert result["participants"][0]["id"] == "user-1"
    assert result["participants"][0]["display_name"] == "User One"
    assert result["participants"][0]["email"] == "user1@example.com"
    assert result["participants"][0]["roles"] == ["owner"]


def test_send_channel_message_helper_sends_message():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    created_message = SimpleNamespace(id="msg-1")

    client = MagicMock()
    channel = client.teams.by_team_id.return_value.channels.by_channel_id.return_value
    channel.messages.post = AsyncMock(return_value=created_message)

    result = asyncio.run(
        personal_assistant.send_channel_message(
            client,
            team_id="team-1",
            channel_id="channel-1",
            message="hello",
            content_type="text",
        )
    )

    assert result["status"] == "sent"
    assert result["team_id"] == "team-1"
    assert result["channel_id"] == "channel-1"
    assert result["message_id"] == "msg-1"
    channel.messages.post.assert_awaited_once()