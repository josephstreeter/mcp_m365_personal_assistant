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


def test_get_todo_lists_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def get_todo_lists(self, _client, **kwargs):
            return {"lists": [{"id": "l1"}]}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.get_todo_lists())
    data = json.loads(payload)

    assert data["lists"][0]["id"] == "l1"


def test_update_todo_task_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def update_todo_task(self, _client, **kwargs):
            return {**kwargs, "status": "updated"}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(
        module.update_todo_task(
            list_id="list-1",
            task_id="task-1",
            title="Updated",
            due_date="2026-06-20T09:00:00Z",
            status="inProgress",
        )
    )
    data = json.loads(payload)

    assert data["status"] == "updated"
    assert data["list_id"] == "list-1"
    assert data["task_id"] == "task-1"
    assert data["status"] == "updated"


def test_delete_todo_task_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def delete_todo_task(self, _client, **kwargs):
            return {"status": "deleted", **kwargs}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.delete_todo_task(list_id="list-1", task_id="task-1"))
    data = json.loads(payload)

    assert data["status"] == "deleted"
    assert data["list_id"] == "list-1"
    assert data["task_id"] == "task-1"


def test_create_todo_list_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def create_todo_list(self, _client, **kwargs):
            return {"status": "created", "list": {"id": "l2", "display_name": kwargs["display_name"]}}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.create_todo_list(display_name="Personal"))
    data = json.loads(payload)

    assert data["status"] == "created"
    assert data["list"]["display_name"] == "Personal"


def test_update_todo_task_wrapper_rejects_invalid_status(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def update_todo_task(self, _client, **kwargs):
            raise AssertionError("update_todo_task helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.update_todo_task(list_id="list-1", task_id="task-1", status="bad"))
    data = json.loads(payload)

    assert "error" in data
    assert "status must be one of" in data["error"].lower()


def test_update_todo_task_wrapper_requires_patch_fields(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def update_todo_task(self, _client, **kwargs):
            raise AssertionError("update_todo_task helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.update_todo_task(list_id="list-1", task_id="task-1"))
    data = json.loads(payload)

    assert "error" in data
    assert "at least one of" in data["error"].lower()


def test_delete_todo_task_wrapper_rejects_empty_task_id(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def delete_todo_task(self, _client, **kwargs):
            raise AssertionError("delete_todo_task helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.delete_todo_task(list_id="list-1", task_id="  "))
    data = json.loads(payload)

    assert "error" in data
    assert "task_id is required" in data["error"].lower()


def test_create_todo_list_wrapper_rejects_empty_display_name(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def create_todo_list(self, _client, **kwargs):
            raise AssertionError("create_todo_list helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.create_todo_list(display_name="  "))
    data = json.loads(payload)

    assert "error" in data
    assert "display_name is required" in data["error"].lower()


def test_get_todo_lists_helper_shapes_response():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    lists_response = SimpleNamespace(
        value=[
            SimpleNamespace(id="l1", display_name="Tasks", is_shared=False, wellknown_list_name=SimpleNamespace(value="defaultList"))
        ]
    )

    client = MagicMock()
    client.me.todo.lists.get = AsyncMock(return_value=lists_response)

    result = asyncio.run(personal_assistant.get_todo_lists(client))

    assert len(result["lists"]) == 1
    assert result["lists"][0]["id"] == "l1"
    assert result["lists"][0]["display_name"] == "Tasks"


def test_update_todo_task_helper_patches_task():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    updated_task = SimpleNamespace(id="task-1")
    client = MagicMock()
    target = client.me.todo.lists.by_todo_task_list_id.return_value.tasks.by_todo_task_id.return_value
    target.patch = AsyncMock(return_value=updated_task)

    result = asyncio.run(
        personal_assistant.update_todo_task(
            client,
            list_id="list-1",
            task_id="task-1",
            title="Updated",
            due_date="2026-06-20T09:00:00Z",
            status="completed",
        )
    )

    assert result["status"] == "updated"
    assert result["list_id"] == "list-1"
    assert result["task_id"] == "task-1"
    target.patch.assert_awaited_once()


def test_delete_todo_task_helper_deletes_task():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    client = MagicMock()
    target = client.me.todo.lists.by_todo_task_list_id.return_value.tasks.by_todo_task_id.return_value
    target.delete = AsyncMock(return_value=None)

    result = asyncio.run(personal_assistant.delete_todo_task(client, list_id="list-1", task_id="task-1"))

    assert result["status"] == "deleted"
    assert result["list_id"] == "list-1"
    assert result["task_id"] == "task-1"
    target.delete.assert_awaited_once()


def test_create_todo_list_helper_creates_list():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    created_list = SimpleNamespace(id="l2", display_name="Personal")
    client = MagicMock()
    client.me.todo.lists.post = AsyncMock(return_value=created_list)

    result = asyncio.run(personal_assistant.create_todo_list(client, display_name="Personal"))

    assert result["status"] == "created"
    assert result["list"]["id"] == "l2"
    assert result["list"]["display_name"] == "Personal"
