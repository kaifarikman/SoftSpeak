from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.crud import notifications as notifications_crud
from src.db.crud import push_notifications as push_notifications_crud
from src.db.crud.auth import get_user_by_email
from src.db.session import get_db
from src.db.models import User
from src.services.push_notifications import get_public_key_base64

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationSchema(BaseModel):
    chat_id: int
    chat_name: str
    chat_type: str
    unread_count: int
    last_message: str
    last_message_time: str


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class BrowserPushSubscription(BaseModel):
    endpoint: str
    expiration_time: int | float | None = Field(default=None, alias="expirationTime")
    keys: PushSubscriptionKeys

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class PushConfigResponse(BaseModel):
    enabled: bool
    public_key: str


class PushSubscriptionResponse(BaseModel):
    success: bool
    message: str


async def _get_active_user(email: str, session: AsyncSession) -> User:
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован администратором. Доступ запрещен.",
        )
    return user


@router.get("/{email}", response_model=list[NotificationSchema])
async def get_notifications(
    email: str, session: AsyncSession = Depends(get_db)
) -> list[NotificationSchema]:
    user = await _get_active_user(email, session)
    notifications = await notifications_crud.get_unread_notifications(session, user.id)
    return [
        NotificationSchema(
            chat_id=notif["chat_id"],
            chat_name=notif["chat_name"],
            chat_type=notif["chat_type"],
            unread_count=notif["unread_count"],
            last_message=notif["last_message"],
            last_message_time=notif["last_message_time"],
        )
        for notif in notifications
    ]


@router.get("/push/config", response_model=PushConfigResponse)
async def get_push_config() -> PushConfigResponse:
    return PushConfigResponse(
        enabled=True,
        public_key=get_public_key_base64(),
    )


@router.post(
    "/push/{email}", response_model=PushSubscriptionResponse, status_code=status.HTTP_200_OK
)
async def register_push_subscription(
    email: str,
    subscription: BrowserPushSubscription,
    session: AsyncSession = Depends(get_db),
) -> PushSubscriptionResponse:
    user = await _get_active_user(email, session)
    await push_notifications_crud.upsert_push_subscription(
        session,
        user_id=user.id,
        endpoint=subscription.endpoint,
        p256dh=subscription.keys.p256dh,
        auth=subscription.keys.auth,
        expiration_time=subscription.expiration_time,
    )
    return PushSubscriptionResponse(
        success=True, message="Push-уведомления подключены"
    )


@router.delete("/push/{email}", response_model=PushSubscriptionResponse)
async def unregister_push_subscription(
    email: str,
    endpoint: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_db),
) -> PushSubscriptionResponse:
    user = await _get_active_user(email, session)
    removed = await push_notifications_crud.remove_push_subscription(
        session, user_id=user.id, endpoint=endpoint
    )
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подписка не найдена",
        )
    return PushSubscriptionResponse(
        success=True, message="Push-уведомления отключены"
    )
