from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.security import hash_password, verify_password
from src.db.models import EmailVerificationCode, User

FORBIDDEN_USERNAMES = {
    "admin", "administrator", "root", "system", "support", "help",
    "moderator", "mod", "staff", "team", "service", "api", "bot",
    "test", "testing", "demo", "example", "null", "undefined", "none",
    "softspeak", "soft", "speak", "anonymous", "anon", "user", "users",
    "mail", "email", "www", "http", "https", "ftp", "localhost",
    "server", "client", "db", "database", "sql", "postgres", "mysql"
}


async def get_user_by_username(
    session: AsyncSession,
    username: str,
) -> Optional[User]:
    stmt = select(User).where(User.username == username)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def authenticate_user(
    session: AsyncSession,
    username: str,
    password: str,
) -> Optional[User]:
    user = await get_user_by_username(session, username)
    if not user:
        return None
    
    if not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def _generate_verification_code() -> str:
    length = settings.verification_code_length
    max_value = 10**length
    from secrets import randbelow

    return f"{randbelow(max_value):0{length}d}"


async def issue_email_verification_code(
    session: AsyncSession,
    *,
    username: str,
    email: str,
    raw_password: str,
) -> Tuple[User, EmailVerificationCode]:
    username_lower = username.lower().strip()
    for forbidden in FORBIDDEN_USERNAMES:
        if username_lower == forbidden.lower():
            raise ValueError(f"Никнейм не может быть '{forbidden}'")

    user = await get_user_by_username(session, username)

    existing_email_owner = await get_user_by_email(session, email)
    if existing_email_owner and (not user or existing_email_owner.id != user.id):
        raise ValueError("Почта уже используется другим аккаунтом.")

    password_hash = hash_password(raw_password)

    if user:
        if user.is_active:
            raise ValueError(f"Пользователь с именем '{username}' уже существует и подтвержден. Пожалуйста, войдите в систему.")
        
        # Проверяем, не забанен ли пользователь (если у него есть email, значит он был активен ранее)
        if not user.is_active and user.email:
            raise ValueError("Ваш аккаунт заблокирован администратором. Доступ запрещен.")

        user.email = email
        user.password_hash = password_hash
    else:
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            is_active=False,
            ai_enabled=True,
            messengers_enabled=False,
            settings_enabled=True,
            anonym=True,
        )
        session.add(user)
        await session.flush()

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.verification_code_ttl_min
    )

    verification_code = EmailVerificationCode(
        user_id=user.id,
        code=_generate_verification_code(),
        expires_at=expires_at,
        is_used=False,
    )
    session.add(verification_code)

    await session.commit()
    await session.refresh(user)
    await session.refresh(verification_code)
    return user, verification_code


async def confirm_email_verification_code(
    session: AsyncSession,
    *,
    username: str,
    code: str,
) -> Optional[User]:
    user = await get_user_by_username(session, username)
    if not user:
        return None

    now = datetime.now(timezone.utc)

    stmt: Select[EmailVerificationCode] = select(EmailVerificationCode).where(
        and_(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.code == code,
            EmailVerificationCode.is_used.is_(False),
            EmailVerificationCode.expires_at >= now,
        )
    ).order_by(EmailVerificationCode.id.desc())

    result = await session.execute(stmt)
    verification_code = result.scalar_one_or_none()

    if not verification_code:
        return None

    verification_code.is_used = True
    user.is_active = True

    await session.commit()
    await session.refresh(user)
    return user
