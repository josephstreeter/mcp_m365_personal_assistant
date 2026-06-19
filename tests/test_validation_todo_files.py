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


def test_create_todo_task_wrapper_rejects_empty_list_name(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def create_todo_task(self, _client, **kwargs):
            raise AssertionError("create_todo_task helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.create_todo_task(list_name="   ", title="Task"))
    data = json.loads(payload)

    assert "error" in data
    assert "list_name is required" in data["error"].lower()
    assert data["error_type"] == "ValidationError"
    assert data["retryable"] is False


def test_create_todo_task_wrapper_rejects_empty_title(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def create_todo_task(self, _client, **kwargs):
            raise AssertionError("create_todo_task helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.create_todo_task(list_name="Inbox", title="   "))
    data = json.loads(payload)

    assert "error" in data
    assert "title is required" in data["error"].lower()


def test_create_todo_task_wrapper_rejects_invalid_due_date(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def create_todo_task(self, _client, **kwargs):
            raise AssertionError("create_todo_task helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.create_todo_task(list_name="Inbox", title="Task", due_date="not-a-date"))
    data = json.loads(payload)

    assert "error" in data
    assert "due_date must be an iso 8601 datetime" in data["error"].lower()


def test_complete_todo_task_wrapper_rejects_empty_list_name(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def complete_todo_task(self, _client, **kwargs):
            raise AssertionError("complete_todo_task helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.complete_todo_task(list_name="   ", task_title="Task"))
    data = json.loads(payload)

    assert "error" in data
    assert "list_name is required" in data["error"].lower()


def test_complete_todo_task_wrapper_rejects_empty_task_title(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def complete_todo_task(self, _client, **kwargs):
            raise AssertionError("complete_todo_task helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.complete_todo_task(list_name="Inbox", task_title="   "))
    data = json.loads(payload)

    assert "error" in data
    assert "task_title is required" in data["error"].lower()


def test_get_recent_files_wrapper_rejects_invalid_top(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def get_recent_files(self, _client, **kwargs):
            raise AssertionError("get_recent_files helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.get_recent_files(top=0))
    data = json.loads(payload)

    assert "error" in data
    assert "between 1 and 200" in data["error"].lower()


def test_search_files_wrapper_rejects_empty_query(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def search_files(self, _client, **kwargs):
            raise AssertionError("search_files helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.search_files(query="   "))
    data = json.loads(payload)

    assert "error" in data
    assert "query is required" in data["error"].lower()


def test_search_files_wrapper_rejects_invalid_top(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def search_files(self, _client, **kwargs):
            raise AssertionError("search_files helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.search_files(query="report", top=201))
    data = json.loads(payload)

    assert "error" in data
    assert "between 1 and 200" in data["error"].lower()
