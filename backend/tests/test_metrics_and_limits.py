from __future__ import annotations

from collections import deque
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


class MetricResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


@pytest.mark.anyio
async def test_metrics_endpoint_reports_ws_and_queue_stats(client, fake_session, monkeypatch):
    now = datetime.now(timezone.utc)
    fake_session.execute = AsyncMock(
        return_value=MetricResult(
            [now - timedelta(seconds=30), now - timedelta(seconds=90)]
        )
    )
    monkeypatch.setattr(
        "src.api.metrics.matchmaking_manager",
        SimpleNamespace(active_connections={"u1": object(), "u2": object()}),
    )
    monkeypatch.setattr(
        "src.api.metrics.chat_manager",
        SimpleNamespace(chat_connections={1: {"a": object()}, 2: {"b": object(), "c": object()}}),
    )

    response = await client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert "softspeak_active_ws_connections 5" in body
    assert "softspeak_matchmaking_queue_size 2" in body
    assert "softspeak_matchmaking_wait_seconds{quantile=\"0.5\"}" in body
    assert "softspeak_matchmaking_wait_seconds{quantile=\"0.95\"}" in body


@pytest.mark.anyio
async def test_email_request_rate_limit_blocks_after_five_attempts(
    client, fake_session, fake_user_factory, monkeypatch
):
    from src.api.auth import _email_request_attempts

    _email_request_attempts.clear()

    pending_user = fake_user_factory(
        id=42,
        nickname="newuser",
        email="newuser@example.com",
        is_active=False,
    )
    verification_code = SimpleNamespace(code="123456")

    monkeypatch.setattr(
        "src.api.auth.get_user_by_nickname", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "src.api.auth.issue_email_verification_code",
        AsyncMock(return_value=(pending_user, verification_code)),
    )
    send_email_mock = AsyncMock()
    monkeypatch.setattr("src.api.auth.send_verification_code_email", send_email_mock)

    payload = {
        "nickname": "newuser",
        "email": "newuser@example.com",
        "password": "supersecret1",
    }

    for _ in range(5):
        response = await client.post("/auth/email/request", json=payload)
        assert response.status_code == 200

    limited_response = await client.post("/auth/email/request", json=payload)

    assert limited_response.status_code == 429
    assert "Слишком много запросов" in limited_response.text
    assert send_email_mock.await_count == 5
    _email_request_attempts.clear()
