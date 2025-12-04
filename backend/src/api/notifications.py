from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from src.db.session import get_db
from src.db.crud.auth import get_user_by_email
from src.db.crud import notifications as notifications_crud

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationSchema(BaseModel):
    chat_id: int
    chat_name: str
    chat_type: str
    unread_count: int
    last_message: str
    last_message_time: str


@router.get("/{email}", response_model=list[NotificationSchema])
async def get_notifications(
    email: str,
    session: AsyncSession = Depends(get_db),
) -> list[NotificationSchema]:
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован администратором. Доступ запрещен.",
        )
    
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

