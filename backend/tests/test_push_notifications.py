from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.mark.anyio
async def test_push_config_endpoint_returns_public_key(client):
    response = await client.get("/notifications/push/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is True
    assert isinstance(payload["public_key"], str)
    assert len(payload["public_key"]) > 0


@pytest.mark.anyio
async def test_register_and_unregister_push_subscription(
    client, monkeypatch, fake_user_factory
):
    user = fake_user_factory(id=21, email="push@example.com")

    monkeypatch.setattr(
        "src.api.notifications.get_user_by_email", AsyncMock(return_value=user)
    )
    upsert_mock = AsyncMock(return_value=SimpleNamespace(id=1))
    remove_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "src.api.notifications.push_notifications_crud.upsert_push_subscription",
        upsert_mock,
    )
    monkeypatch.setattr(
        "src.api.notifications.push_notifications_crud.remove_push_subscription",
        remove_mock,
    )

    response = await client.post(
        "/notifications/push/push@example.com",
        json={
            "endpoint": "https://example.com/push/1",
            "expirationTime": None,
            "keys": {"p256dh": "key", "auth": "secret"},
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    upsert_mock.assert_awaited_once()

    delete_response = await client.delete(
        "/notifications/push/push@example.com",
        params={"endpoint": "https://example.com/push/1"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True
    remove_mock.assert_awaited_once()
