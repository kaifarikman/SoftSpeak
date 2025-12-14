from typing import Optional
import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import User
from src.core.security import verify_password, hash_password
from src.db.crud.auth import get_user_by_nickname

FORBIDDEN_USERNAMES = {
    "admin",
    "administrator",
    "root",
    "system",
    "support",
    "help",
    "moderator",
    "mod",
    "staff",
    "team",
    "service",
    "api",
    "bot",
    "test",
    "testing",
    "demo",
    "example",
    "null",
    "undefined",
    "none",
    "softspeak",
    "soft",
    "speak",
    "anonymous",
    "anon",
    "user",
    "users",
    "mail",
    "email",
    "www",
    "http",
    "https",
    "ftp",
    "localhost",
    "server",
    "client",
    "db",
    "database",
    "sql",
    "postgres",
    "mysql",
}


async def update_username(
    session: AsyncSession, user_id: int, new_nickname: str
) -> tuple[bool, Optional[str]]:
    new_nickname = new_nickname.strip()
    if not re.match("^[a-zA-Zа-яА-ЯёЁ0-9_-]+$", new_nickname):
        return (
            False,
            "Никнейм может содержать только английские и русские буквы, цифры, дефисы и подчеркивания",
        )
    if len(new_nickname) < 3:
        return (False, "Никнейм должен быть не менее 3 символов")
    if len(new_nickname) > 15:
        return (False, "Слишком длинный nickname")
    nickname_lower = new_nickname.lower()
    for forbidden in FORBIDDEN_USERNAMES:
        if nickname_lower == forbidden.lower():
            return (False, f"Никнейм не может быть '{forbidden}'")
    existing_user = await get_user_by_nickname(session, new_nickname)
    if existing_user and existing_user.id != user_id:
        return (False, "Никнейм занят")
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if not user:
        return (False, "Пользователь не найден")
    user.nickname = new_nickname
    await session.commit()
    return (True, None)


async def update_bio(
    session: AsyncSession, user_id: int, bio: Optional[str]
) -> tuple[bool, Optional[str]]:
    if bio and len(bio) > 100:
        return (False, "Информация о себе не может быть длиннее 100 символов")
    if bio and any((ord(char) < 32 and char not in "\n\r\t" for char in bio)):
        return (False, "Недопустимые символы в тексте")
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if not user:
        return (False, "Пользователь не найден")
    user.bio = bio
    await session.commit()
    return (True, None)


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
    session: AsyncSession, user_id: int, old_password: str, new_password: str
) -> tuple[bool, Optional[str]]:
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if not user:
        return (False, "Пользователь не найден")
    if not verify_password(old_password, user.password_hash):
        return (False, "Неправильный пароль")
    if len(new_password) < 8:
        return (False, "Новый пароль должен быть не менее 8 символов")
    user.password_hash = hash_password(new_password)
    await session.commit()
    return (True, None)
