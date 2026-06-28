from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.core.security import create_access_token
from src.schemas.chat import ChatResponse


@pytest.mark.anyio
async def test_auth_registration_verification_login_and_me(
    client, monkeypatch, fake_user_factory, fake_chat_response
):
    pending_user = fake_user_factory(
        id=10,
        nickname="newuser",
        email="newuser@example.com",
        is_active=False,
    )
    verified_user = fake_user_factory(
        id=10,
        nickname="newuser",
        email="newuser@example.com",
        is_active=True,
    )
    verification_code = SimpleNamespace(code="123456")

    async def fake_issue_email_verification_code(*args, **kwargs):
        return pending_user, verification_code

    monkeypatch.setattr(
        "src.api.auth.get_user_by_nickname", AsyncMock(return_value=None)
    )
    send_email_mock = AsyncMock()
    monkeypatch.setattr(
        "src.api.auth.issue_email_verification_code",
        fake_issue_email_verification_code,
    )
    monkeypatch.setattr("src.api.auth.send_verification_code_email", send_email_mock)
    monkeypatch.setattr(
        "src.api.auth.confirm_email_verification_code",
        AsyncMock(return_value=verified_user),
    )
    monkeypatch.setattr(
        "src.api.auth.authenticate_user", AsyncMock(return_value=verified_user)
    )
    monkeypatch.setattr(
        "src.api.auth.get_user_by_email", AsyncMock(return_value=verified_user)
    )
    monkeypatch.setattr(
        "src.api.auth.get_chat_data_for_user", AsyncMock(return_value=fake_chat_response)
    )

    request_response = await client.post(
        "/auth/email/request",
        json={
            "nickname": "newuser",
            "email": "newuser@example.com",
            "password": "supersecret1",
        },
    )
    assert request_response.status_code == 200
    assert request_response.json() == {
        "message": "Код подтверждения отправлен на указанную почту."
    }
    send_email_mock.assert_awaited_once_with("newuser@example.com", "123456")

    confirm_response = await client.post(
        "/auth/email/confirm",
        json={"nickname": "newuser", "code": "123456"},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["message"] == (
        "Email подтвержден. Теперь вы можете войти по логину и паролю."
    )

    login_response = await client.post(
        "/auth/login",
        json={"email": "newuser@example.com", "password": "supersecret1"},
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["email"] == "newuser@example.com"
    assert login_payload["nickname"] == "newuser"
    assert login_payload["chat_data"] == fake_chat_response.model_dump()
    assert "softspeak_refresh=" in login_response.headers.get("set-cookie", "")

    token = create_access_token("newuser@example.com")
    me_response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json() == {
        "nickname": "newuser",
        "email": "newuser@example.com",
        "chat_data": fake_chat_response.model_dump(),
        "is_banned": False,
    }


@pytest.mark.anyio
async def test_email_domains_endpoint_returns_whitelist(client):
    response = await client.get("/auth/email/domains")
    assert response.status_code == 200
    assert response.json() == ["example.com"]
