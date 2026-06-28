from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


class TagResult:
    def __init__(self, values):
        self._values = values

    def scalar_one_or_none(self):
        return self._values

    def scalars(self):
        return self

    def all(self):
        return self._values


@pytest.mark.anyio
async def test_tags_endpoints_return_and_store_user_tags(client, fake_session, monkeypatch):
    user = SimpleNamespace(id=7, email="tagged@example.com")
    tags = [
        SimpleNamespace(id=1, name="Психология", emoji="🧠"),
        SimpleNamespace(id=2, name="Кино", emoji="🎬"),
        SimpleNamespace(id=3, name="Музыка", emoji="🎵"),
    ]

    async def fake_execute(statement):
        statement_text = str(statement)
        if "FROM users" in statement_text:
            return TagResult(user)
        if "SELECT interest_tags.id FROM interest_tags" in statement_text:
            return TagResult([1, 2, 3])
        if "FROM interest_tags" in statement_text:
            return TagResult(tags)
        return TagResult(None)

    fake_session.execute = AsyncMock(side_effect=fake_execute)
    fake_session.add = lambda obj: None
    fake_session.commit = AsyncMock()
    monkeypatch.setattr("src.api.tags._get_user_or_404", AsyncMock(return_value=user))

    response = await client.get("/tags")
    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "name": "Психология", "emoji": "🧠"},
        {"id": 2, "name": "Кино", "emoji": "🎬"},
        {"id": 3, "name": "Музыка", "emoji": "🎵"},
    ]

    user_response = await client.get("/tags/user/tagged@example.com")
    assert user_response.status_code == 200
    assert user_response.json() == [
        {"id": 1, "name": "Психология", "emoji": "🧠"},
        {"id": 2, "name": "Кино", "emoji": "🎬"},
        {"id": 3, "name": "Музыка", "emoji": "🎵"},
    ]

    set_response = await client.post(
        "/tags/user/tagged@example.com",
        json={"tag_ids": [1, 2, 3]},
    )
    assert set_response.status_code == 200
    assert set_response.json() == {"ok": True, "tag_ids": [1, 2, 3]}
    assert fake_session.commit.await_count >= 1
