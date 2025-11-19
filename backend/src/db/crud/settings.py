"""CRUD-операции для настроек пользователя."""
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import User, Blacklist
from src.core.security import verify_password, hash_password
from src.db.crud.auth import get_user_by_username


async def update_username(session: AsyncSession, user_id: int, new_username: str) -> tuple[bool, Optional[str]]:
    """
    Обновляет username пользователя.
    
    Returns:
        (success: bool, error_message: Optional[str])
    """
    # Проверяем, что новый username не занят
    existing_user = await get_user_by_username(session, new_username)
    if existing_user and existing_user.id != user_id:
        return False, "Никнейм занят"
    
    # Проверяем формат username (только буквы, цифры, подчеркивания)
    if not new_username.replace('_', '').replace('-', '').isalnum():
        return False, "Никнейм может содержать только буквы, цифры, дефисы и подчеркивания"
    
    if len(new_username) < 3 or len(new_username) > 32:
        return False, "Никнейм должен быть от 3 до 32 символов"
    
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        return False, "Пользователь не найден"
    
    user.username = new_username
    await session.commit()
    return True, None


async def update_bio(session: AsyncSession, user_id: int, bio: Optional[str]) -> tuple[bool, Optional[str]]:
    """
    Обновляет информацию о себе (bio).
    
    Returns:
        (success: bool, error_message: Optional[str])
    """
    if bio and len(bio) > 500:
        return False, "Информация о себе не может быть длиннее 500 символов"
    
    # Проверка на недопустимые символы (можно расширить)
    if bio and any(ord(char) < 32 and char not in '\n\r\t' for char in bio):
        return False, "Недопустимые символы в тексте"
    
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        return False, "Пользователь не найден"
    
    user.bio = bio
    await session.commit()
    return True, None


async def update_notification_settings(
    session: AsyncSession,
    user_id: int,
    notification_anon_chats: Optional[bool] = None,
    notification_open_chats: Optional[bool] = None,
) -> Optional[User]:
    """Обновляет настройки уведомлений."""
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        return None
    
    if notification_anon_chats is not None:
        user.notification_anon_chats = notification_anon_chats
    if notification_open_chats is not None:
        user.notification_open_chats = notification_open_chats
    
    await session.commit()
    await session.refresh(user)
    return user


async def update_media_settings(
    session: AsyncSession,
    user_id: int,
    media_auto_upload_photos: Optional[bool] = None,
    media_auto_upload_videos: Optional[bool] = None,
) -> Optional[User]:
    """Обновляет настройки медиа."""
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        return None
    
    if media_auto_upload_photos is not None:
        user.media_auto_upload_photos = media_auto_upload_photos
    if media_auto_upload_videos is not None:
        user.media_auto_upload_videos = media_auto_upload_videos
    
    await session.commit()
    await session.refresh(user)
    return user


async def change_password(
    session: AsyncSession,
    user_id: int,
    old_password: str,
    new_password: str,
) -> tuple[bool, Optional[str]]:
    """
    Изменяет пароль пользователя.
    
    Returns:
        (success: bool, error_message: Optional[str])
    """
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        return False, "Пользователь не найден"
    
    # Проверяем старый пароль
    if not verify_password(old_password, user.password_hash):
        return False, "Неправильный пароль"
    
    # Проверяем новый пароль
    if len(new_password) < 8:
        return False, "Новый пароль должен быть не менее 8 символов"
    
    # Обновляем пароль
    user.password_hash = hash_password(new_password)
    await session.commit()
    return True, None


async def add_to_blacklist(session: AsyncSession, user_id: int, blocked_username: str) -> tuple[bool, Optional[str]]:
    """
    Добавляет пользователя в черный список.
    
    Returns:
        (success: bool, error_message: Optional[str])
    """
    # Нельзя заблокировать самого себя
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        return False, "Пользователь не найден"
    
    if user.username == blocked_username:
        return False, "Нельзя заблокировать самого себя"
    
    # Находим пользователя для блокировки
    blocked_user = await get_user_by_username(session, blocked_username)
    if not blocked_user:
        return False, "Пользователь не найден"
    
    # Проверяем, не заблокирован ли уже
    existing_stmt = select(Blacklist).where(
        and_(
            Blacklist.user_id == user_id,
            Blacklist.blocked_user_id == blocked_user.id
        )
    )
    existing_result = await session.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        return False, "Пользователь уже в черном списке"
    
    # Добавляем в черный список
    blacklist_entry = Blacklist(
        user_id=user_id,
        blocked_user_id=blocked_user.id,
    )
    session.add(blacklist_entry)
    await session.commit()
    return True, None


async def remove_from_blacklist(session: AsyncSession, user_id: int, blocked_username: str) -> tuple[bool, Optional[str]]:
    """
    Удаляет пользователя из черного списка.
    
    Returns:
        (success: bool, error_message: Optional[str])
    """
    blocked_user = await get_user_by_username(session, blocked_username)
    if not blocked_user:
        return False, "Пользователь не найден"
    
    stmt = select(Blacklist).where(
        and_(
            Blacklist.user_id == user_id,
            Blacklist.blocked_user_id == blocked_user.id
        )
    )
    result = await session.execute(stmt)
    blacklist_entry = result.scalar_one_or_none()
    
    if not blacklist_entry:
        return False, "Пользователь не найден в черном списке"
    
    await session.delete(blacklist_entry)
    await session.commit()
    return True, None


async def get_blacklist(session: AsyncSession, user_id: int) -> List[User]:
    """Получает список заблокированных пользователей."""
    stmt = (
        select(User)
        .join(Blacklist, User.id == Blacklist.blocked_user_id)
        .where(Blacklist.user_id == user_id)
        .order_by(Blacklist.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())

