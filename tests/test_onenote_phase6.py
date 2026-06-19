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


def test_get_onenote_page_content_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def get_onenote_page_content(self, _client, **kwargs):
            return {"page_id": kwargs["page_id"], "title": "Title", "content_html": "<p>hello</p>"}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.get_onenote_page_content(page_id="p1"))
    data = json.loads(payload)

    assert data["page_id"] == "p1"
    assert data["title"] == "Title"


def test_create_onenote_page_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def create_onenote_page(self, _client, **kwargs):
            return {
                "status": "created",
                "page": {"id": "p2", "title": kwargs["title"], "web_url": "https://example"},
            }

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.create_onenote_page(section_id="s1", title="Plan", content_html="<p>Body</p>"))
    data = json.loads(payload)

    assert data["status"] == "created"
    assert data["page"]["id"] == "p2"
    assert data["page"]["title"] == "Plan"


def test_get_onenote_page_content_wrapper_rejects_empty_page_id(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def get_onenote_page_content(self, _client, **kwargs):
            raise AssertionError("get_onenote_page_content helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.get_onenote_page_content(page_id="  "))
    data = json.loads(payload)

    assert "error" in data
    assert "page_id is required" in data["error"].lower()


def test_create_onenote_page_wrapper_rejects_empty_content(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def create_onenote_page(self, _client, **kwargs):
            raise AssertionError("create_onenote_page helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.create_onenote_page(section_id="s1", title="Plan", content_html="  "))
    data = json.loads(payload)

    assert "error" in data
    assert "content_html is required" in data["error"].lower()


def test_get_onenote_page_content_helper_shapes_response():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    client = MagicMock()
    target = client.me.onenote.pages.by_onenote_page_id.return_value
    target.get = AsyncMock(return_value=SimpleNamespace(title="Weekly Plan"))
    target.content.get = AsyncMock(return_value=b"<html><body>Plan</body></html>")

    result = asyncio.run(personal_assistant.get_onenote_page_content(client, page_id="p1"))

    assert result["page_id"] == "p1"
    assert result["title"] == "Weekly Plan"
    assert "<html>" in result["content_html"]


def test_create_onenote_page_helper_shapes_created_page():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    created_page = SimpleNamespace(
        id="p2",
        title="New Page",
        links=SimpleNamespace(one_note_web_url=SimpleNamespace(href="https://example/page")),
    )

    client = MagicMock()
    client.me.onenote.sections.by_onenote_section_id.return_value.pages.post = AsyncMock(return_value=created_page)

    result = asyncio.run(
        personal_assistant.create_onenote_page(
            client,
            section_id="s1",
            title="New Page",
            content_html="<html><body>Body</body></html>",
        )
    )

    assert result["status"] == "created"
    assert result["page"]["id"] == "p2"
    assert result["page"]["title"] == "New Page"
    assert result["page"]["web_url"] == "https://example/page"
