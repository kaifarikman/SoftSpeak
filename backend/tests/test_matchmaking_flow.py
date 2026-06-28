from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.mark.anyio
async def test_matchmaking_start_finds_chat_and_notifies_both_users(
    client, monkeypatch, fake_user_factory, fake_session
):
    user_a = fake_user_factory(id=1, nickname="alice", email="alice@example.com")
    user_b = fake_user_factory(id=2, nickname="bob", email="bob@example.com")
    chat = SimpleNamespace(id=77, user1_id=1, user2_id=2)

    fake_session.users_by_id = {1: user_a, 2: user_b}

    async def fake_get_user_by_email(session, email):
        return user_a if email == user_a.email else user_b

    async def fake_find_match(session, user_id, threshold=None):
        return chat if user_id == user_b.id else None

    async def fake_join_matchmaking_queue(session, user_id):
        return SimpleNamespace(user_id=user_id, is_searching=True)

    monkeypatch.setattr("src.api.matchmaking.get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(
        "src.api.matchmaking.has_completed_profile", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        "src.api.matchmaking.join_matchmaking_queue", fake_join_matchmaking_queue
    )
    monkeypatch.setattr(
        "src.api.matchmaking.leave_matchmaking_queue", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        "src.api.matchmaking.get_matchmaking_queue_count",
        AsyncMock(side_effect=[1, 0]),
    )
    monkeypatch.setattr("src.api.matchmaking.find_match", fake_find_match)
    send_personal_message = AsyncMock()
    monkeypatch.setattr(
        "src.api.matchmaking.matchmaking_manager",
        SimpleNamespace(send_personal_message=send_personal_message),
    )
    monkeypatch.setattr(
        "src.api.matchmaking.send_push_notifications_for_user",
        AsyncMock(return_value=1),
    )

    first_response = await client.post("/matchmaking/start/alice@example.com")
    assert first_response.status_code == 200
    assert first_response.json() == {
        "is_searching": True,
        "queue_count": 1,
        "chat_id": None,
    }

    second_response = await client.post("/matchmaking/start/bob@example.com")
    assert second_response.status_code == 200
    assert second_response.json() == {
        "is_searching": False,
        "queue_count": 0,
        "chat_id": 77,
    }

    assert send_personal_message.await_count == 2
    payloads = [call.args[0] for call in send_personal_message.await_args_list]
    assert {"type": "match_found", "chat_id": 77} in payloads
