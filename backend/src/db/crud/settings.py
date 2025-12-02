from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import User, Blacklist
from src.core.security import verify_password, hash_password
from src.db.crud.auth import get_user_by_username

FORBIDDEN_USERNAMES = {
    "admin", "administrator", "root", "system", "support", "help",
    "moderator", "mod", "staff", "team", "service", "api", "bot",
    "test", "testing", "demo", "example", "null", "undefined", "none",
    "softspeak", "soft", "speak", "anonymous", "anon", "user", "users",
    "mail", "email", "www", "http", "https", "ftp", "localhost",
    "server", "client", "db", "database", "sql", "postgres", "mysql"
}


async def update_username(session: AsyncSession, user_id: int, new_username: str) -> tuple[bool, Optional[str]]:
    existing_user = await get_user_by_username(session, new_username)
    if existing_user and existing_user.id != user_id:
        return False, "Никнейм занят"
    
    if not new_username.replace('_', '').replace('-', '').isalnum():
        return False, "Никнейм может содержать только буквы, цифры, дефисы и подчеркивания"
    
    if len(new_username) < 3 or len(new_username) > 32:
        return False, "Никнейм должен быть от 3 до 32 символов"
    
    username_lower = new_username.lower().strip()
    for forbidden in FORBIDDEN_USERNAMES:
        if username_lower == forbidden.lower():
            return False, f"Никнейм не может быть '{forbidden}'"
    
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        return False, "Пользователь не найден"
    
    user.username = new_username
    await session.commit()
    return True, None


async def update_bio(session: AsyncSession, user_id: int, bio: Optional[str]) -> tuple[bool, Optional[str]]:
    if bio and len(bio) > 500:
        return False, "Информация о себе не может быть длиннее 500 символов"
    
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


async def change_password(
    session: AsyncSession,
    user_id: int,
    old_password: str,
    new_password: str,
) -> tuple[bool, Optional[str]]:
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        return False, "Пользователь не найден"
    
    if not verify_password(old_password, user.password_hash):
        return False, "Неправильный пароль"
    
    if len(new_password) < 8:
        return False, "Новый пароль должен быть не менее 8 символов"
    
    user.password_hash = hash_password(new_password)
    await session.commit()
    return True, None


async def add_to_blacklist(session: AsyncSession, user_id: int, blocked_username: str) -> tuple[bool, Optional[str]]:
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        return False, "Пользователь не найден"
    
    if user.username == blocked_username:
        return False, "Нельзя заблокировать самого себя"
    
    blocked_user = await get_user_by_username(session, blocked_username)
    if not blocked_user:
        return False, "Пользователь не найден"
    
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
    
    blacklist_entry = Blacklist(
        user_id=user_id,
        blocked_user_id=blocked_user.id,
    )
    session.add(blacklist_entry)
    await session.commit()
    return True, None


async def remove_from_blacklist(session: AsyncSession, user_id: int, blocked_username: str) -> tuple[bool, Optional[str]]:
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
    stmt = (
        select(User)
        .join(Blacklist, User.id == Blacklist.blocked_user_id)
        .where(Blacklist.user_id == user_id)
        .order_by(Blacklist.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())

