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


def test_list_drive_items_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def list_drive_items(self, _client, **kwargs):
            return {"items": [{"id": "i1"}], "next_link": None, **kwargs}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.list_drive_items(item_id="folder-1", top=25))
    data = json.loads(payload)

    assert data["items"][0]["id"] == "i1"
    assert data["item_id"] == "folder-1"
    assert data["top"] == 25


def test_create_share_link_wrapper_normalizes_inputs(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def create_share_link(self, _client, **kwargs):
            return {"status": "created", **kwargs}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.create_share_link(item_id="file-1", link_type="EDIT", scope="ORGANIZATION"))
    data = json.loads(payload)

    assert data["status"] == "created"
    assert data["item_id"] == "file-1"
    assert data["link_type"] == "edit"
    assert data["scope"] == "organization"


def test_upload_small_text_file_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def upload_small_text_file(self, _client, **kwargs):
            return {"status": "uploaded", **kwargs}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(
        module.upload_small_text_file(
            file_name="notes.txt",
            content="hello",
            parent_item_id=None,
            content_type="text/plain",
        )
    )
    data = json.loads(payload)

    assert data["status"] == "uploaded"
    assert data["file_name"] == "notes.txt"


def test_list_drive_items_wrapper_rejects_invalid_top(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def list_drive_items(self, _client, **kwargs):
            raise AssertionError("list_drive_items helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.list_drive_items(top=0))
    data = json.loads(payload)

    assert "error" in data
    assert "between 1 and 200" in data["error"].lower()


def test_create_share_link_wrapper_rejects_invalid_link_type(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def create_share_link(self, _client, **kwargs):
            raise AssertionError("create_share_link helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.create_share_link(item_id="i1", link_type="download"))
    data = json.loads(payload)

    assert "error" in data
    assert "link_type must be one of" in data["error"].lower()


def test_upload_small_text_file_wrapper_rejects_empty_content(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def upload_small_text_file(self, _client, **kwargs):
            raise AssertionError("upload_small_text_file helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.upload_small_text_file(file_name="a.txt", content="   "))
    data = json.loads(payload)

    assert "error" in data
    assert "content is required" in data["error"].lower()


def test_list_drive_items_helper_shapes_response():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    children_response = SimpleNamespace(
        value=[
            SimpleNamespace(
                id="i1",
                name="Documents",
                folder=SimpleNamespace(),
                size=1024,
                web_url="https://contoso/documents",
                last_modified_date_time=None,
            )
        ],
        odata_next_link="https://graph.microsoft.com/v1.0/next",
    )

    client = MagicMock()
    client.me.drive.get = AsyncMock(return_value=SimpleNamespace(id="drive-1"))
    client.drives.by_drive_id.return_value.root.children.get = AsyncMock(return_value=children_response)

    result = asyncio.run(personal_assistant.list_drive_items(client, item_id=None, top=5))

    assert result["items"][0]["id"] == "i1"
    assert result["items"][0]["is_folder"] is True
    assert result["next_link"] == "https://graph.microsoft.com/v1.0/next"


def test_create_share_link_helper_returns_link():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    permission = SimpleNamespace(link=SimpleNamespace(web_url="https://contoso/share"))

    client = MagicMock()
    client.me.drive.get = AsyncMock(return_value=SimpleNamespace(id="drive-1"))
    target = client.drives.by_drive_id.return_value.items.by_drive_item_id.return_value
    target.create_link.post = AsyncMock(return_value=permission)

    result = asyncio.run(personal_assistant.create_share_link(client, item_id="file-1", link_type="view", scope="organization"))

    assert result["status"] == "created"
    assert result["item_id"] == "file-1"
    assert result["web_url"] == "https://contoso/share"
    assert result["link_type"] == "view"
    assert result["scope"] == "organization"


def test_upload_small_text_file_helper_uploads_content():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    created_item = SimpleNamespace(id="file-1", name="notes.txt", web_url=None, size=None)
    uploaded_item = SimpleNamespace(id="file-1", name="notes.txt", web_url="https://contoso/notes.txt", size=5)

    client = MagicMock()
    client.me.drive.get = AsyncMock(return_value=SimpleNamespace(id="drive-1"))
    drive_builder = client.drives.by_drive_id.return_value
    drive_builder.root.children.post = AsyncMock(return_value=created_item)
    drive_builder.items.by_drive_item_id.return_value.content.put = AsyncMock(return_value=uploaded_item)

    result = asyncio.run(
        personal_assistant.upload_small_text_file(
            client,
            file_name="notes.txt",
            content="hello",
            parent_item_id=None,
            content_type="text/plain",
        )
    )

    assert result["status"] == "uploaded"
    assert result["item"]["id"] == "file-1"
    assert result["item"]["name"] == "notes.txt"
    assert result["item"]["web_url"] == "https://contoso/notes.txt"

    put_mock = drive_builder.items.by_drive_item_id.return_value.content.put
    assert put_mock.await_args.args[0] == b"hello"