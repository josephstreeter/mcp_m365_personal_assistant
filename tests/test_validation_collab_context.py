import asyncio
import importlib
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


@pytest.fixture
def configured_main(monkeypatch):
    monkeypatch.setenv("client_id", "test-client-id")
    monkeypatch.setenv("tenant_id", "test-tenant-id")

    module = importlib.import_module("main")
    monkeypatch.setattr(module, "get_singleton_client", lambda: object())
    return module


def test_get_contacts_wrapper_rejects_invalid_top(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def get_contacts(self, _client, **kwargs):
            raise AssertionError("get_contacts helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.get_contacts(top=0))
    data = json.loads(payload)

    assert "error" in data
    assert "between 1 and 200" in data["error"].lower()
    assert data["error_type"] == "ValidationError"
    assert data["retryable"] is False


def test_get_teams_chats_wrapper_rejects_invalid_top(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def get_teams_chats(self, _client, **kwargs):
            raise AssertionError("get_teams_chats helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.get_teams_chats(top=201))
    data = json.loads(payload)

    assert "error" in data
    assert "between 1 and 200" in data["error"].lower()


def test_get_chat_messages_wrapper_rejects_empty_chat_id(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def get_chat_messages(self, _client, **kwargs):
            raise AssertionError("get_chat_messages helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.get_chat_messages(chat_id="   ", top=10))
    data = json.loads(payload)

    assert "error" in data
    assert "chat_id is required" in data["error"].lower()


def test_send_chat_message_wrapper_rejects_missing_target(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def send_chat_message(self, _client, **kwargs):
            raise AssertionError("send_chat_message helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.send_chat_message(message="hello", recipient=None, chat_id=None))
    data = json.loads(payload)

    assert "error" in data
    assert "either recipient or chat_id is required" in data["error"].lower()


def test_send_chat_message_wrapper_rejects_invalid_content_type(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def send_chat_message(self, _client, **kwargs):
            raise AssertionError("send_chat_message helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.send_chat_message(message="hello", chat_id="c1", content_type="markdown"))
    data = json.loads(payload)

    assert "error" in data
    assert "content_type must be one of" in data["error"].lower()


def test_get_user_presence_wrapper_rejects_empty_user_ids(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def get_user_presence(self, _client, **kwargs):
            raise AssertionError("get_user_presence helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.get_user_presence(user_ids=[]))
    data = json.loads(payload)

    assert "error" in data
    assert "at least one user id" in data["error"].lower()


def test_get_relevant_people_wrapper_rejects_invalid_top(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def get_relevant_people(self, _client, **kwargs):
            raise AssertionError("get_relevant_people helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.get_relevant_people(top=0))
    data = json.loads(payload)

    assert "error" in data
    assert "between 1 and 200" in data["error"].lower()


def test_get_trending_files_wrapper_rejects_invalid_top(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def get_trending_files(self, _client, **kwargs):
            raise AssertionError("get_trending_files helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.get_trending_files(top=201))
    data = json.loads(payload)

    assert "error" in data
    assert "between 1 and 200" in data["error"].lower()


def test_get_onenote_pages_wrapper_rejects_empty_section_id(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def get_onenote_pages(self, _client, **kwargs):
            raise AssertionError("get_onenote_pages helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.get_onenote_pages(section_id="   ", top=10))
    data = json.loads(payload)

    assert "error" in data
    assert "section_id is required" in data["error"].lower()


def test_get_onenote_pages_wrapper_rejects_invalid_top(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def get_onenote_pages(self, _client, **kwargs):
            raise AssertionError("get_onenote_pages helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.get_onenote_pages(section_id="s1", top=0))
    data = json.loads(payload)

    assert "error" in data
    assert "between 1 and 200" in data["error"].lower()
