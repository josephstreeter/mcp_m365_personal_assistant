import asyncio
import importlib
import json
import pathlib
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


def _load_main_with_env(monkeypatch):
    monkeypatch.setenv("client_id", "test-client-id")
    monkeypatch.setenv("tenant_id", "test-tenant-id")

    module = importlib.import_module("main")
    monkeypatch.setattr(module, "get_singleton_client", lambda: object())
    return module


def test_update_calendar_event_wrapper(monkeypatch):
    module = _load_main_with_env(monkeypatch)

    class _FakeAssistant:
        async def update_calendar_event(self, _client, **kwargs):
            return {"status": "updated", **kwargs}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(
        module.update_calendar_event(
            event_id="e1",
            subject="Updated",
            start="2026-06-18T10:00:00Z",
            end="2026-06-18T10:30:00Z",
            attendees=["a@example.com"],
            location="Room A",
            body="Agenda",
            is_all_day=False,
        )
    )
    data = json.loads(payload)

    assert data["status"] == "updated"
    assert data["event_id"] == "e1"
    assert data["subject"] == "Updated"


def test_delete_calendar_event_wrapper(monkeypatch):
    module = _load_main_with_env(monkeypatch)

    class _FakeAssistant:
        async def delete_calendar_event(self, _client, **kwargs):
            return {"status": "deleted", **kwargs}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.delete_calendar_event(event_id="e2"))
    data = json.loads(payload)

    assert data["status"] == "deleted"
    assert data["event_id"] == "e2"


def test_respond_to_event_wrapper(monkeypatch):
    module = _load_main_with_env(monkeypatch)

    class _FakeAssistant:
        async def respond_to_event(self, _client, **kwargs):
            return {"status": "responded", **kwargs}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.respond_to_event(event_id="e3", response="accept", comment="ok", send_response=True))
    data = json.loads(payload)

    assert data["status"] == "responded"
    assert data["response"] == "accept"


def test_find_meeting_times_wrapper(monkeypatch):
    module = _load_main_with_env(monkeypatch)

    class _FakeAssistant:
        async def find_meeting_times(self, _client, **kwargs):
            return {"suggestions": [], **kwargs}

    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(
        module.find_meeting_times(
            attendees=["a@example.com"],
            duration_minutes=30,
            time_window_start="2026-06-18T09:00:00Z",
            time_window_end="2026-06-18T17:00:00Z",
            max_candidates=5,
        )
    )
    data = json.loads(payload)

    assert data["attendees"] == ["a@example.com"]
    assert data["duration_minutes"] == 30
    assert data["max_candidates"] == 5


def test_delete_calendar_event_helper_calls_delete():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    target = MagicMock()
    target.delete = AsyncMock(return_value=None)

    client = MagicMock()
    client.me.events.by_event_id.return_value = target

    result = asyncio.run(personal_assistant.delete_calendar_event(client, event_id="e2"))

    assert result["status"] == "deleted"
    assert result["event_id"] == "e2"
    target.delete.assert_awaited_once()


def test_respond_to_event_helper_rejects_invalid_response():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    client = MagicMock()

    result = asyncio.run(
        personal_assistant.respond_to_event(
            client,
            event_id="e3",
            response="maybe",
            comment=None,
            send_response=True,
        )
    )

    assert "error" in result
    assert "invalid response" in result["error"].lower()


def test_find_meeting_times_helper_validates_attendees():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    client = MagicMock()

    result = asyncio.run(
        personal_assistant.find_meeting_times(
            client,
            attendees=[],
            duration_minutes=30,
            time_window_start="2026-06-18T09:00:00Z",
            time_window_end="2026-06-18T17:00:00Z",
            max_candidates=3,
        )
    )

    assert "error" in result
    assert "at least one attendee" in result["error"].lower()


def test_find_meeting_times_helper_shapes_schedule_items():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    schedule_item = SimpleNamespace(
        status=SimpleNamespace(value="free"),
        start=SimpleNamespace(date_time="2026-06-18T10:00:00Z"),
        end=SimpleNamespace(date_time="2026-06-18T10:30:00Z"),
        subject="",
        location="",
        is_private=False,
    )
    schedule_info = SimpleNamespace(schedule_id="a@example.com", schedule_items=[schedule_item])
    schedule_response = SimpleNamespace(value=[schedule_info])

    client = MagicMock()
    client.me.calendar.get_schedule.post = AsyncMock(return_value=schedule_response)

    result = asyncio.run(
        personal_assistant.find_meeting_times(
            client,
            attendees=["a@example.com"],
            duration_minutes=30,
            time_window_start="2026-06-18T09:00:00Z",
            time_window_end="2026-06-18T17:00:00Z",
            max_candidates=3,
        )
    )

    assert len(result["suggestions"]) == 1
    assert result["suggestions"][0]["attendee"] == "a@example.com"
    assert result["suggestions"][0]["status"] == "free"
    assert result["duration_minutes"] == 30


def test_update_calendar_event_helper_sets_fields():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    updated = SimpleNamespace(
        id="e1",
        subject="Updated",
        start=SimpleNamespace(date_time="2026-06-18T10:00:00Z"),
        end=SimpleNamespace(date_time="2026-06-18T10:30:00Z"),
    )

    target = MagicMock()
    target.patch = AsyncMock(return_value=updated)

    client = MagicMock()
    client.me.events.by_event_id.return_value = target

    result = asyncio.run(
        personal_assistant.update_calendar_event(
            client,
            event_id="e1",
            subject="Updated",
            start="2026-06-18T10:00:00Z",
            end="2026-06-18T10:30:00Z",
            attendees=["a@example.com"],
            location="Room A",
            body="Agenda",
            is_all_day=False,
        )
    )

    assert result["status"] == "updated"
    assert result["event_id"] == "e1"
    assert result["subject"] == "Updated"
    target.patch.assert_awaited_once()


def test_respond_to_event_helper_accept_path():
    personal_assistant = importlib.import_module("modules.personal_assistant")

    target = MagicMock()
    target.accept.post = AsyncMock(return_value=None)

    client = MagicMock()
    client.me.events.by_event_id.return_value = target

    result = asyncio.run(
        personal_assistant.respond_to_event(
            client,
            event_id="e3",
            response="accept",
            comment="Sounds good",
            send_response=True,
        )
    )

    assert result["status"] == "responded"
    assert result["response"] == "accept"
    target.accept.post.assert_awaited_once()


def test_update_calendar_event_wrapper_rejects_invalid_start(monkeypatch):
    module = _load_main_with_env(monkeypatch)

    class _GuardAssistant:
        async def update_calendar_event(self, _client, **kwargs):
            raise AssertionError("update_calendar_event helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.update_calendar_event(event_id="e1", start="not-a-datetime"))
    data = json.loads(payload)

    assert "error" in data
    assert "iso 8601" in data["error"].lower()
    assert data["error_type"] == "ValidationError"
    assert data["retryable"] is False


def test_delete_calendar_event_wrapper_rejects_empty_event_id(monkeypatch):
    module = _load_main_with_env(monkeypatch)

    class _GuardAssistant:
        async def delete_calendar_event(self, _client, **kwargs):
            raise AssertionError("delete_calendar_event helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.delete_calendar_event(event_id="   "))
    data = json.loads(payload)

    assert "error" in data
    assert "event_id is required" in data["error"].lower()


def test_respond_to_event_wrapper_rejects_invalid_response(monkeypatch):
    module = _load_main_with_env(monkeypatch)

    class _GuardAssistant:
        async def respond_to_event(self, _client, **kwargs):
            raise AssertionError("respond_to_event helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(module.respond_to_event(event_id="e3", response="maybe"))
    data = json.loads(payload)

    assert "error" in data
    assert "must be one of" in data["error"].lower()


def test_find_meeting_times_wrapper_rejects_invalid_max_candidates(monkeypatch):
    module = _load_main_with_env(monkeypatch)

    class _GuardAssistant:
        async def find_meeting_times(self, _client, **kwargs):
            raise AssertionError("find_meeting_times helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(
        module.find_meeting_times(
            attendees=["a@example.com"],
            duration_minutes=30,
            time_window_start="2026-06-18T09:00:00Z",
            time_window_end="2026-06-18T17:00:00Z",
            max_candidates=0,
        )
    )
    data = json.loads(payload)

    assert "error" in data
    assert "between 1 and 50" in data["error"].lower()


def test_find_meeting_times_wrapper_rejects_invalid_window_start(monkeypatch):
    module = _load_main_with_env(monkeypatch)

    class _GuardAssistant:
        async def find_meeting_times(self, _client, **kwargs):
            raise AssertionError("find_meeting_times helper should not be called")

    monkeypatch.setattr(module, "personal_assistant", _GuardAssistant())

    payload = asyncio.run(
        module.find_meeting_times(
            attendees=["a@example.com"],
            duration_minutes=30,
            time_window_start="bad-start",
            time_window_end="2026-06-18T17:00:00Z",
            max_candidates=5,
        )
    )
    data = json.loads(payload)

    assert "error" in data
    assert "time_window_start" in data["error"].lower()
