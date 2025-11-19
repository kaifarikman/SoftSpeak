"""API эндпоинты для настроек пользователя."""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional
import os
import uuid
from pathlib import Path

from src.db.session import get_db
from src.db.crud.auth import get_user_by_username
from src.db.crud import settings as settings_crud
from src.schemas.chat import ChatResponse
from src.api.chat import get_chat_data_for_user

router = APIRouter(prefix="/settings", tags=["settings"])


# ==================== Схемы запросов ====================

class UpdateUsernameRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)


class UpdateBioRequest(BaseModel):
    bio: Optional[str] = Field(None, max_length=500)


class UpdateNotificationSettingsRequest(BaseModel):
    notification_anon_chats: Optional[bool] = None
    notification_open_chats: Optional[bool] = None


class UpdateMediaSettingsRequest(BaseModel):
    media_auto_upload_photos: Optional[bool] = None
    media_auto_upload_videos: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)
    new_password_confirm: str


class AddToBlacklistRequest(BaseModel):
    username: str


class RemoveFromBlacklistRequest(BaseModel):
    username: str


# ==================== Схемы ответов ====================

class SettingsResponse(BaseModel):
    success: bool
    message: str
    chat_data: Optional[dict] = None


class BlacklistUserResponse(BaseModel):
    id: int
    username: str
    avatar: Optional[str] = None

    class Config:
        from_attributes = True


class UserSettingsResponse(BaseModel):
    """Полные настройки пользователя."""
    username: str
    bio: Optional[str] = None
    avatar: Optional[str] = None
    notification_anon_chats: bool
    notification_open_chats: bool
    media_auto_upload_photos: bool
    media_auto_upload_videos: bool

    class Config:
        from_attributes = True


# ==================== Профиль ====================

@router.put("/profile/username/{username}", response_model=SettingsResponse)
async def update_username_endpoint(
    username: str,
    request: UpdateUsernameRequest,
    session: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Обновляет никнейм пользователя."""
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    success, error_message = await settings_crud.update_username(
        session, user.id, request.username
    )
    
    if not success:
        return SettingsResponse(
            success=False,
            message=error_message or "Ошибка обновления никнейма",
        )
    
    # Обновляем chat_data
    chat_data = await get_chat_data_for_user(session, request.username)
    
    return SettingsResponse(
        success=True,
        message="Никнейм изменен",
        chat_data=chat_data.model_dump(),
    )


@router.put("/profile/avatar/{username}", response_model=SettingsResponse)
async def update_avatar_endpoint(
    username: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Загружает аватар пользователя."""
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    # Проверяем формат файла
    allowed_extensions = {'.jpg', '.jpeg', '.png'}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ''
    
    if file_ext not in allowed_extensions:
        return SettingsResponse(
            success=False,
            message="Неправильный формат или слишком большой размер файла",
        )
    
    # Проверяем размер файла (10 МБ)
    max_size = 10 * 1024 * 1024  # 10 МБ
    contents = await file.read()
    
    if len(contents) > max_size:
        return SettingsResponse(
            success=False,
            message="Неправильный формат или слишком большой размер файла",
        )
    
    # Сохраняем файл
    static_dir = Path(__file__).parent.parent.parent / "static"
    upload_dir = static_dir / "uploads" / "avatars"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Генерируем уникальное имя файла
    file_id = str(uuid.uuid4())
    file_path = upload_dir / f"{file_id}{file_ext}"
    
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Обновляем путь к аватару в БД
    avatar_url = f"/static/uploads/avatars/{file_id}{file_ext}"
    
    # Удаляем старый аватар, если есть
    if user.avatar and user.avatar.startswith("/static/uploads/avatars/"):
        old_path = static_dir / user.avatar.lstrip("/static/")
        if old_path.exists():
            old_path.unlink()
    
    user.avatar = avatar_url
    await session.commit()
    
    # Обновляем chat_data
    chat_data = await get_chat_data_for_user(session, username)
    
    return SettingsResponse(
        success=True,
        message="Фотография профиля изменена",
        chat_data=chat_data.model_dump(),
    )


@router.put("/profile/bio/{username}", response_model=SettingsResponse)
async def update_bio_endpoint(
    username: str,
    request: UpdateBioRequest,
    session: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Обновляет информацию о себе."""
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
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


# ==================== Уведомления ====================

@router.put("/notifications/{username}", response_model=SettingsResponse)
async def update_notification_settings_endpoint(
    username: str,
    request: UpdateNotificationSettingsRequest,
    session: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Обновляет настройки уведомлений."""
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
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


# ==================== Медиа ====================

@router.put("/media/{username}", response_model=SettingsResponse)
async def update_media_settings_endpoint(
    username: str,
    request: UpdateMediaSettingsRequest,
    session: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Обновляет настройки медиа."""
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    updated_user = await settings_crud.update_media_settings(
        session,
        user.id,
        media_auto_upload_photos=request.media_auto_upload_photos,
        media_auto_upload_videos=request.media_auto_upload_videos,
    )
    
    if not updated_user:
        return SettingsResponse(
            success=False,
            message="Ошибка обновления настроек",
        )
    
    return SettingsResponse(
        success=True,
        message="Настройки медиа обновлены",
    )


# ==================== Аккаунт ====================

@router.put("/account/password/{username}", response_model=SettingsResponse)
async def change_password_endpoint(
    username: str,
    request: ChangePasswordRequest,
    session: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Изменяет пароль пользователя."""
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    # Проверяем совпадение новых паролей
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


# ==================== Черный список ====================

@router.get("/blacklist/{username}", response_model=list[BlacklistUserResponse])
async def get_blacklist_endpoint(
    username: str,
    session: AsyncSession = Depends(get_db),
) -> list[BlacklistUserResponse]:
    """Получает список заблокированных пользователей."""
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    blocked_users = await settings_crud.get_blacklist(session, user.id)
    
    return [
        BlacklistUserResponse(
            id=u.id,
            username=u.username,
            avatar=u.avatar or None,
        )
        for u in blocked_users
    ]


@router.post("/blacklist/{username}", response_model=SettingsResponse)
async def add_to_blacklist_endpoint(
    username: str,
    request: AddToBlacklistRequest,
    session: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Добавляет пользователя в черный список."""
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
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


@router.delete("/blacklist/{username}", response_model=SettingsResponse)
async def remove_from_blacklist_endpoint(
    username: str,
    blocked_username: str,
    session: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Удаляет пользователя из черного списка."""
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
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


# ==================== Получение настроек (должен быть последним) ====================

@router.get("/{username}", response_model=UserSettingsResponse)
async def get_user_settings(
    username: str,
    session: AsyncSession = Depends(get_db),
) -> UserSettingsResponse:
    """Получает все настройки пользователя."""
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    return UserSettingsResponse(
        username=user.username,
        bio=user.bio,
        avatar=user.avatar,
        notification_anon_chats=user.notification_anon_chats,
        notification_open_chats=user.notification_open_chats,
        media_auto_upload_photos=user.media_auto_upload_photos,
        media_auto_upload_videos=user.media_auto_upload_videos,
    )

