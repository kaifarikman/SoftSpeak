from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import WebSocketDisconnect


class DummyTask:
    def done(self):
        return True

    def cancel(self):
        return None


class FakeWebSocket:
    def __init__(self):
        self.sent = []
        self.client_state = SimpleNamespace(name="CONNECTED")

    async def accept(self):
        return None

    async def send_json(self, payload):
        self.sent.append(payload)

    async def receive_text(self):
        raise WebSocketDisconnect(code=1000)

    async def close(self, code=1000, reason=None):
        self.client_state = SimpleNamespace(name="DISCONNECTED")


@pytest.mark.anyio
async def test_matchmaking_websocket_schedules_search_loop(
    monkeypatch, fake_user_factory, fake_session
):
    user = fake_user_factory(id=1, nickname="alice", email="alice@example.com")
    fake_session.users_by_id = {1: user}

    class FakeResult:
        def __init__(self, value):
            self.value = value

        def scalar_one_or_none(self):
            return self.value

    async def fake_execute(statement):
        if "matchmaking_queue" in str(statement):
            return FakeResult(SimpleNamespace(user_id=user.id, is_searching=True))
        return FakeResult(None)

    fake_session.execute = fake_execute

    async def fake_get_user_by_email(session, email):
        return user

    async def fake_has_completed_profile(session, user_id):
        return True

    async def fake_get_matchmaking_queue_count(session, exclude_user_id=None):
        return 0

    async def fake_leave_matchmaking_queue(session, user_id):
        return True

    @asynccontextmanager
    async def fake_session_cm():
        yield fake_session

    scheduled_tasks = []

    def fake_create_task(coro):
        code = getattr(coro, "cr_code", None)
        scheduled_tasks.append(getattr(code, "co_name", getattr(coro, "__name__", type(coro).__name__)))
        return DummyTask()

    monkeypatch.setattr("src.api.matchmaking.enforce_ws_rate_limit", AsyncMock(return_value=True))
    monkeypatch.setattr("src.api.matchmaking.get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr("src.api.matchmaking.has_completed_profile", fake_has_completed_profile)
    monkeypatch.setattr(
        "src.api.matchmaking.get_matchmaking_queue_count",
        fake_get_matchmaking_queue_count,
    )
    monkeypatch.setattr(
        "src.api.matchmaking.leave_matchmaking_queue",
        fake_leave_matchmaking_queue,
    )
    monkeypatch.setattr(
        "src.api.matchmaking.AsyncSessionLocal",
        fake_session_cm,
    )
    monkeypatch.setattr("src.api.matchmaking.matchmaking_manager", SimpleNamespace(
        connect=AsyncMock(return_value=None),
        disconnect=lambda email: None,
        searching_users={},
        send_personal_message=AsyncMock(return_value=None),
    ))
    monkeypatch.setattr("src.api.matchmaking.asyncio.create_task", fake_create_task)

    from src.api.matchmaking import matchmaking_websocket

    websocket = FakeWebSocket()
    await matchmaking_websocket(websocket, user.email)

    assert "ping_loop" in scheduled_tasks
    assert "search_loop" in scheduled_tasks
    assert any(payload.get("type") == "connected" for payload in websocket.sent)
