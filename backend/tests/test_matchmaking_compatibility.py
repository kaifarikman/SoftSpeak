from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


class QueryResult:
    def __init__(self, values):
        self._values = values

    def scalar_one_or_none(self):
        return self._values if not isinstance(self._values, list) else None

    def scalars(self):
        return self

    def all(self):
        return self._values if isinstance(self._values, list) else [self._values]


@pytest.mark.anyio
async def test_get_chat_compatibility_returns_score_and_common_tags(
    client, fake_session, monkeypatch, fake_user_factory
):
    user = fake_user_factory(id=1, email="alice@example.com")
    chat = SimpleNamespace(
        id=77,
        user1_id=1,
        user2_id=2,
        is_active=True,
        is_public=True,
        similarity_score=0.87,
    )

    async def fake_get_user_by_email(session, email):
        return user

    async def fake_get_anonymous_chat(session, chat_id, user_id):
        return chat if chat_id == chat.id and user_id == user.id else None

    responses = iter(
        [
            QueryResult([1, 2, 3]),
            QueryResult([2, 3, 4]),
            QueryResult(
                [
                    SimpleNamespace(id=2, name="Кино", emoji="🎬"),
                    SimpleNamespace(id=3, name="Музыка", emoji="🎵"),
                ]
            ),
        ]
    )

    async def fake_execute(statement):
        return next(responses)

    fake_session.execute = AsyncMock(side_effect=fake_execute)
    monkeypatch.setattr("src.api.matchmaking.get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(
        "src.api.matchmaking.get_anonymous_chat", fake_get_anonymous_chat
    )

    response = await client.get("/matchmaking/chat/77/compatibility?email=alice@example.com")

    assert response.status_code == 200
    assert response.json() == {
        "score": 87,
        "common_tags": [
            {"name": "Кино", "emoji": "🎬"},
            {"name": "Музыка", "emoji": "🎵"},
        ],
    }


@pytest.mark.anyio
async def test_close_chat_marks_chat_inactive_and_stores_reason(
    client, fake_session, monkeypatch, fake_user_factory
):
    user = fake_user_factory(id=1, email="alice@example.com")
    chat = SimpleNamespace(
        id=77,
        user1_id=1,
        user2_id=2,
        is_active=True,
        close_reason=None,
    )

    async def fake_get_user_by_email(session, email):
        return user

    async def fake_get_anonymous_chat(session, chat_id, user_id):
        return chat if chat_id == chat.id and user_id == user.id else None

    fake_session.commit = AsyncMock()
    monkeypatch.setattr("src.api.matchmaking.get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(
        "src.api.matchmaking.get_anonymous_chat", fake_get_anonymous_chat
    )

    response = await client.post(
        "/matchmaking/chat/77/close?email=alice@example.com&reason=boring"
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "chat_id": 77}
    assert chat.is_active is False
    assert chat.close_reason == "boring"
    assert fake_session.commit.await_count == 1
