from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional

from src.db.session import get_db
from src.db.crud.auth import get_user_by_email, get_user_by_nickname
from src.db.crud import settings as settings_crud
from src.schemas.chat import ChatResponse
from src.api.chat import get_chat_data_for_user

router = APIRouter(prefix="/settings", tags=["settings"])


async def verify_user_active(email: str, session: AsyncSession) -> None:
    """Проверяет, что пользователь активен (не забанен). Выбрасывает HTTPException если забанен."""
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

class UpdateNicknameRequest(BaseModel):
    nickname: str = Field(..., min_length=3, max_length=32)

class UpdateBioRequest(BaseModel):
    bio: Optional[str] = Field(None, max_length=500)

class UpdateNotificationSettingsRequest(BaseModel):
    notification_anon_chats: Optional[bool] = None
    notification_open_chats: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)
    new_password_confirm: str


class AddToBlacklistRequest(BaseModel):
    username: str


class RemoveFromBlacklistRequest(BaseModel):
    username: str


class SettingsResponse(BaseModel):
    success: bool
    message: str
    chat_data: Optional[dict] = None

class BlacklistUserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True

class UserSettingsResponse(BaseModel):
    username: str
    bio: Optional[str] = None
    notification_anon_chats: bool
    notification_open_chats: bool

    class Config:
        from_attributes = True

@router.put("/profile/nickname/{email}", response_model=SettingsResponse)
async def update_nickname_endpoint(
    email: str,
    request: UpdateNicknameRequest,
    session: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    await verify_user_active(email, session)
    user = await get_user_by_email(session, email)
    
    success, error_message = await settings_crud.update_username(
        session, user.id, request.nickname
    )
    
    if not success:
        return SettingsResponse(
            success=False,
            message=error_message or "Ошибка обновления никнейма",
        )
    
    chat_data = await get_chat_data_for_user(session, email)
    
    return SettingsResponse(
        success=True,
        message="Никнейм изменен",
        chat_data=chat_data.model_dump(),
    )


@router.put("/profile/bio/{email}", response_model=SettingsResponse)
async def update_bio_endpoint(
    email: str,
    request: UpdateBioRequest,
    session: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    await verify_user_active(email, session)
    user = await get_user_by_email(session, email)
    
    success, error_message = await settings_crud.update_bio(
        session, user.id, request.bio
    )
    
    if not success:
        return SettingsResponse(
            success=False,
            message=error_message or "Ошибка обновления информации",
        )
    
    return SettingsResponse(
        success=True,
        message="Информация изменена",
    )


@router.put("/notifications/{email}", response_model=SettingsResponse)
async def update_notification_settings_endpoint(
    email: str,
    request: UpdateNotificationSettingsRequest,
    session: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    await verify_user_active(email, session)
    user = await get_user_by_email(session, email)
    
    updated_user = await settings_crud.update_notification_settings(
        session,
        user.id,
        notification_anon_chats=request.notification_anon_chats,
        notification_open_chats=request.notification_open_chats,
    )
    
    if not updated_user:
        return SettingsResponse(
            success=False,
            message="Ошибка обновления настроек",
        )
    
    return SettingsResponse(
        success=True,
        message="Настройки уведомлений обновлены",
    )


@router.put("/account/password/{email}", response_model=SettingsResponse)
async def change_password_endpoint(
    email: str,
    request: ChangePasswordRequest,
    session: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    await verify_user_active(email, session)
    user = await get_user_by_email(session, email)
    
    if request.new_password != request.new_password_confirm:
        return SettingsResponse(
            success=False,
            message="Неправильный пароль или новые пароли не совпадают",
        )
    
    success, error_message = await settings_crud.change_password(
        session,
        user.id,
        request.old_password,
        request.new_password,
    )
    
    if not success:
        return SettingsResponse(
            success=False,
            message=error_message or "Ошибка изменения пароля",
        )
    
    return SettingsResponse(
        success=True,
        message="Пароль изменен",
    )



@router.get("/blacklist/{email}", response_model=list[BlacklistUserResponse])
async def get_blacklist_endpoint(
    email: str,
    session: AsyncSession = Depends(get_db),
) -> list[BlacklistUserResponse]:
    await verify_user_active(email, session)
    user = await get_user_by_email(session, email)
    
    blocked_users = await settings_crud.get_blacklist(session, user.id)
    
    return [
        BlacklistUserResponse(
            id=u.id,
            username=u.nickname,
        )
        for u in blocked_users
    ]


@router.post("/blacklist/{email}", response_model=SettingsResponse)
async def add_to_blacklist_endpoint(
    email: str,
    request: AddToBlacklistRequest,
    session: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    await verify_user_active(email, session)
    user = await get_user_by_email(session, email)
    
    success, error_message = await settings_crud.add_to_blacklist(
        session, user.id, request.username
    )
    
    if not success:
        return SettingsResponse(
            success=False,
            message=error_message or "Ошибка добавления в черный список",
        )
    
    return SettingsResponse(
        success=True,
        message="Пользователь добавлен в черный список",
    )


@router.delete("/blacklist/{email}", response_model=SettingsResponse)
async def remove_from_blacklist_endpoint(
    email: str,
    blocked_username: str,
    session: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    await verify_user_active(email, session)
    user = await get_user_by_email(session, email)
    
    success, error_message = await settings_crud.remove_from_blacklist(
        session, user.id, blocked_username
    )
    
    if not success:
        return SettingsResponse(
            success=False,
            message=error_message or "Ошибка удаления из черного списка",
        )
    
    return SettingsResponse(
        success=True,
        message="Пользователь удален из черного списка",
    )


@router.get("/status/{email}")
async def get_user_status(
    email: str,
    session: AsyncSession = Depends(get_db),
):
    """Проверка статуса пользователя (забанен ли он)"""
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    return {
        "is_banned": user.is_banned,
        "email": user.email,
        "nickname": user.nickname
    }


@router.get("/{email}", response_model=UserSettingsResponse)
async def get_user_settings(
    email: str,
    session: AsyncSession = Depends(get_db),
) -> UserSettingsResponse:
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    # Проверяем, не забанен ли пользователь
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован администратором. Доступ запрещен.",
        )
    
    return UserSettingsResponse(
        username=user.nickname,
        bio=user.bio,
        notification_anon_chats=user.notification_anon_chats,
        notification_open_chats=user.notification_open_chats,
    )

