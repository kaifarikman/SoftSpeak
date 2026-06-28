from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import PushSubscription


def _parse_expiration_time(expiration_time: int | float | None) -> datetime | None:
    if expiration_time is None:
        return None
    try:
        return datetime.fromtimestamp(float(expiration_time) / 1000.0, tz=timezone.utc)
    except (TypeError, ValueError):
        return None


async def upsert_push_subscription(
    session: AsyncSession,
    *,
    user_id: int,
    endpoint: str,
    p256dh: str,
    auth: str,
    expiration_time: int | float | None = None,
) -> PushSubscription:
    stmt = select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    result = await session.execute(stmt)
    subscription = result.scalar_one_or_none()
    parsed_expiration = _parse_expiration_time(expiration_time)
    if subscription:
        subscription.user_id = user_id
        subscription.p256dh = p256dh
        subscription.auth = auth
        subscription.expiration_time = parsed_expiration
        subscription.is_active = True
    else:
        subscription = PushSubscription(
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            expiration_time=parsed_expiration,
            is_active=True,
        )
        session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    return subscription


async def remove_push_subscription(
    session: AsyncSession, *, user_id: int, endpoint: str
) -> bool:
    stmt = select(PushSubscription).where(
        PushSubscription.user_id == user_id,
        PushSubscription.endpoint == endpoint,
    )
    result = await session.execute(stmt)
    subscription = result.scalar_one_or_none()
    if not subscription:
        return False
    await session.delete(subscription)
    await session.commit()
    return True


async def get_active_push_subscriptions(
    session: AsyncSession, user_id: int
) -> list[PushSubscription]:
    stmt = select(PushSubscription).where(
        PushSubscription.user_id == user_id,
        PushSubscription.is_active.is_(True),
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def deactivate_push_subscription(
    session: AsyncSession, endpoint: str
) -> bool:
    stmt = select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    result = await session.execute(stmt)
    subscription = result.scalar_one_or_none()
    if not subscription:
        return False
    subscription.is_active = False
    await session.commit()
    return True

