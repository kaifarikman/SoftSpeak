from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("JWT_SECRET", "test-test-test-test-test-test-test-test")
os.environ.setdefault("DEV_MODE", "true")
os.environ.setdefault("ALLOWED_EMAIL_DOMAINS", "example.com")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/app"
)

from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.db.session import get_db
from src.main import app


@dataclass
class FakeResult:
    value: object | None

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, users_by_id: dict[int, object] | None = None):
        self.users_by_id = users_by_id or {}

    async def execute(self, statement):
        for criterion in getattr(statement, "_where_criteria", ()):
            right = getattr(criterion, "right", None)
            value = getattr(right, "value", None)
            if value in self.users_by_id:
                return FakeResult(self.users_by_id[value])
        return FakeResult(None)

    async def commit(self):
        return None

    async def rollback(self):
        return None

    async def refresh(self, obj):
        return None

    async def delete(self, obj):
        return None


@pytest.fixture
def fake_user_factory():
    def factory(**overrides):
        base = {
            "id": 1,
            "nickname": "tester",
            "email": "tester@example.com",
            "is_active": True,
            "is_banned": False,
            "messengers_enabled": True,
            "settings_enabled": True,
            "anonym": True,
            "full_name": "Test User",
        }
        base.update(overrides)
        return SimpleNamespace(**base)

    return factory


@pytest.fixture
def fake_chat_response():
    from src.schemas.chat import ChatResponse

    return ChatResponse(ai=True, anonym=True, messengers=True, settings=True)


@pytest.fixture
def fake_session():
    return FakeSession()


@pytest.fixture
async def client(fake_session):
    async def override_get_db():
        yield fake_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"
