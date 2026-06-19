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


def test_get_daily_briefing_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def get_daily_briefing(self, _client, **kwargs):
            return {"date": kwargs.get("date_value") or "2026-06-18", "calendar": {"upcoming_events": []}}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.get_daily_briefing(date_value="2026-06-18", timezone_name="UTC"))
    data = json.loads(payload)

    assert data["date"] == "2026-06-18"
    assert data["version"] == 2


def test_prepare_meeting_brief_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def prepare_meeting_brief(self, _client, **kwargs):
            return {"event": {"id": kwargs["event_id"]}, "prep_notes": []}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.prepare_meeting_brief(event_id="e1", include_recent_threads=False))
    data = json.loads(payload)

    assert data["event"]["id"] == "e1"
    assert data["version"] == 2


def test_health_check_wrapper(configured_main, monkeypatch):
    module = configured_main

    class _FakeAssistant:
        async def health_check(self, _client):
            return {
                "status": "ok",
                "graph_reachable": True,
                "auth_valid": True,
                "checked_at": "2026-06-18T00:00:00Z",
                "details": ["ok"],
            }

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.health_check())
    data = json.loads(payload)

    assert data["status"] == "ok"
    assert data["version"] == 2


def test_get_daily_briefing_wrapper_rejects_invalid_date(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def get_daily_briefing(self, _client, **kwargs):
            raise AssertionError("get_daily_briefing helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.get_daily_briefing(date_value="06-18-2026"))
    data = json.loads(payload)

    assert "error" in data
    assert "yyyy-mm-dd" in data["error"].lower()


def test_prepare_meeting_brief_wrapper_rejects_empty_event_id(configured_main, monkeypatch):
    module = configured_main

    class _GuardAssistant:
        async def prepare_meeting_brief(self, _client, **kwargs):
            raise AssertionError("prepare_meeting_brief helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.prepare_meeting_brief(event_id="  "))
    data = json.loads(payload)

    assert "error" in data
    assert "event_id is required" in data["error"].lower()


def test_get_effective_scopes_wrapper_contains_expected_keys(configured_main):
    module = configured_main

    payload = asyncio.run(module.get_effective_scopes())
    data = json.loads(payload)

    assert "configured_scopes" in data
    assert "missing_recommended_scopes" in data
    assert data["version"] == 2


def test_list_supported_tools_wrapper_contains_new_tools(configured_main):
    module = configured_main

    payload = asyncio.run(module.list_supported_tools())
    data = json.loads(payload)

    tool_names = {tool["name"] for tool in data["tools"]}
    assert "get_daily_briefing" in tool_names
    assert "prepare_meeting_brief" in tool_names
    assert "health_check" in tool_names


def test_get_daily_briefing_helper_shapes_summary(monkeypatch):
    personal_assistant = importlib.import_module("modules.personal_assistant")

    monkeypatch.setattr(
        personal_assistant,
        "get_calendar_events",
        AsyncMock(
            return_value=[
                {
                    "subject": "Sync",
                    "start": "2026-06-18T10:00:00Z",
                    "end": "2026-06-18T10:30:00Z",
                }
            ]
        ),
    )
    monkeypatch.setattr(
        personal_assistant,
        "get_messages",
        AsyncMock(return_value=[{"id": "m1", "is_read": False}, {"id": "m2", "is_read": True}]),
    )
    monkeypatch.setattr(
        personal_assistant,
        "get_todo_tasks",
        AsyncMock(return_value=[{"title": "Task", "status": "notStarted", "due": "2026-06-18T12:00:00Z"}]),
    )
    monkeypatch.setattr(personal_assistant, "get_recent_files", AsyncMock(return_value=[{"name": "Doc"}]))
    monkeypatch.setattr(personal_assistant, "get_relevant_people", AsyncMock(return_value=[{"name": "Alex"}]))

    result = asyncio.run(
        personal_assistant.get_daily_briefing(
            MagicMock(),
            date_value="2026-06-18",
            timezone_name="UTC",
        )
    )

    assert result["date"] == "2026-06-18"
    assert result["mail"]["unread_count"] == 1
    assert len(result["calendar"]["upcoming_events"]) == 1


def test_prepare_meeting_brief_helper_shapes_payload():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    client = MagicMock()
    event = SimpleNamespace(
        id="e1",
        subject="Project Sync",
        start=SimpleNamespace(date_time="2026-06-18T10:00:00Z"),
        end=SimpleNamespace(date_time="2026-06-18T10:30:00Z"),
        attendees=[SimpleNamespace(email_address=SimpleNamespace(address="a@example.com"))],
    )
    client.me.events.by_event_id.return_value.get = AsyncMock(return_value=event)

    personal_assistant.get_relevant_people = AsyncMock(return_value=[{"name": "A", "emails": ["a@example.com"]}])
    personal_assistant.search_messages = AsyncMock(return_value=[{"id": "m1"}])
    personal_assistant.search_files = AsyncMock(return_value=[{"name": "file1"}])

    result = asyncio.run(personal_assistant.prepare_meeting_brief(client, event_id="e1", include_recent_threads=True))

    assert result["event"]["id"] == "e1"
    assert len(result["attendee_context"]) == 1
    assert len(result["related_messages"]) == 1
    assert len(result["related_files"]) == 1


def test_health_check_helper_success():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    client = MagicMock()
    client.me.get = AsyncMock(return_value=SimpleNamespace(id="user-1"))

    result = asyncio.run(personal_assistant.health_check(client))

    assert result["status"] == "ok"
    assert result["graph_reachable"] is True
    assert result["auth_valid"] is True
