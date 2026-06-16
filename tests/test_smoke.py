import asyncio
import importlib
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


def test_validate_environment_missing_vars(monkeypatch):
    module = importlib.import_module("modules.graph_client")
    monkeypatch.setenv("client_id", "")
    monkeypatch.setenv("tenant_id", "")

    with pytest.raises(module.ConfigurationError):
        module.validate_environment()


def test_main_tool_wrapper_get_user_profile(monkeypatch):
    monkeypatch.setenv("client_id", "test-client-id")
    monkeypatch.setenv("tenant_id", "test-tenant-id")

    module = importlib.import_module("main")

    class _FakeAssistant:
        async def get_user_profile(self, _client):
            return {"ok": True, "name": "Smoke User"}

    monkeypatch.setattr(module, "get_singleton_client", lambda: object())
    monkeypatch.setattr(module, "personal_assistant", _FakeAssistant())

    payload = asyncio.run(module.get_user_profile())
    assert '"ok": true' in payload
    assert "Smoke User" in payload
