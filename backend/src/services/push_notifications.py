from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any

from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)
from py_vapid import Vapid02
from pywebpush import WebPushException, webpush
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.crud.push_notifications import (
    deactivate_push_subscription,
    get_active_push_subscriptions,
)

logger = logging.getLogger(__name__)
_vapid: Vapid02 | None = None


def _get_vapid() -> Vapid02:
    global _vapid
    if _vapid is None:
        _vapid = Vapid02()
        _vapid.generate_keys()
    return _vapid


def get_public_key_base64() -> str:
    public_key = _get_vapid().public_key
    raw_public_key = public_key.public_bytes(
        encoding=Encoding.X962,
        format=PublicFormat.UncompressedPoint,
    )
    return base64.urlsafe_b64encode(raw_public_key).rstrip(b"=").decode("ascii")


def build_push_payload(
    *,
    title: str,
    body: str,
    url: str = "/home",
    chat_id: int | None = None,
    chat_type: str | None = None,
    unread_count: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": title,
        "body": body,
        "url": url,
    }
    if chat_id is not None:
        payload["chat_id"] = chat_id
    if chat_type is not None:
        payload["chat_type"] = chat_type
    if unread_count is not None:
        payload["unread_count"] = unread_count
    return payload


async def send_push_subscription(subscription, payload: dict[str, Any]) -> None:
    subscription_info = {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh,
            "auth": subscription.auth,
        },
    }
    vapid = _get_vapid()
    try:
        await asyncio.to_thread(
            webpush,
            subscription_info=subscription_info,
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=vapid,
            vapid_claims={"sub": settings.push_vapid_subject},
            ttl=60,
        )
    except WebPushException as exc:
        logger.warning(
            "Web push delivery failed for %s: %s", subscription.endpoint, exc
        )
        raise


async def send_push_notifications_for_user(
    session: AsyncSession, user_id: int, payload: dict[str, Any]
) -> int:
    subscriptions = await get_active_push_subscriptions(session, user_id)
    if not subscriptions:
        return 0

    delivered = 0
    for subscription in subscriptions:
        try:
            await send_push_subscription(subscription, payload)
            delivered += 1
        except WebPushException as exc:
            response = getattr(exc, "response", None)
            status_code = getattr(response, "status_code", None)
            if status_code in (404, 410):
                await deactivate_push_subscription(session, subscription.endpoint)
    return delivered
