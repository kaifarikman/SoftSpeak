"""CRUD и утилиты для генерации случайных псевдонимов."""
from __future__ import annotations

import random

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import RandomNameAdjective, RandomNameNoun

DEFAULT_ADJECTIVES = [
    "Смелый",
    "Весёлый",
    "Таинственный",
    "Лучезарный",
    "Отважный",
    "Игривый",
]

DEFAULT_NOUNS = [
    "Сокол",
    "Енот",
    "Феникс",
    "Лис",
    "Комета",
    "Тигр",
]


async def _get_random_word(session: AsyncSession, model) -> str | None:
    stmt = (
        select(model)
        .where(model.is_active.is_(True))
        .order_by(func.random())
        .limit(1)
    )
    result = await session.execute(stmt)
    obj = result.scalar_one_or_none()
    return obj.text if obj else None


async def generate_random_alias(session: AsyncSession) -> str:
    adjective = await _get_random_word(session, RandomNameAdjective)
    noun = await _get_random_word(session, RandomNameNoun)

    if not adjective:
        adjective = random.choice(DEFAULT_ADJECTIVES)
    if not noun:
        noun = random.choice(DEFAULT_NOUNS)

    return f"{adjective} {noun}"


async def list_adjectives(session: AsyncSession) -> list[RandomNameAdjective]:
    stmt = select(RandomNameAdjective).order_by(RandomNameAdjective.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_nouns(session: AsyncSession) -> list[RandomNameNoun]:
    stmt = select(RandomNameNoun).order_by(RandomNameNoun.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_adjective(session: AsyncSession, word_id: int) -> RandomNameAdjective | None:
    result = await session.execute(
        select(RandomNameAdjective).where(RandomNameAdjective.id == word_id)
    )
    return result.scalar_one_or_none()


async def get_noun(session: AsyncSession, word_id: int) -> RandomNameNoun | None:
    result = await session.execute(
        select(RandomNameNoun).where(RandomNameNoun.id == word_id)
    )
    return result.scalar_one_or_none()


async def create_adjective(session: AsyncSession, text: str) -> RandomNameAdjective:
    normalized = text.strip()
    if not normalized:
        raise ValueError("Текст не может быть пустым")

    existing = await session.execute(
        select(RandomNameAdjective).where(func.lower(RandomNameAdjective.text) == normalized.lower())
    )
    if existing.scalar_one_or_none():
        raise ValueError("Такое прилагательное уже существует")

    word = RandomNameAdjective(text=normalized)
    session.add(word)
    await session.commit()
    await session.refresh(word)
    return word


async def create_noun(session: AsyncSession, text: str) -> RandomNameNoun:
    normalized = text.strip()
    if not normalized:
        raise ValueError("Текст не может быть пустым")

    existing = await session.execute(
        select(RandomNameNoun).where(func.lower(RandomNameNoun.text) == normalized.lower())
    )
    if existing.scalar_one_or_none():
        raise ValueError("Такое существительное уже существует")

    word = RandomNameNoun(text=normalized)
    session.add(word)
    await session.commit()
    await session.refresh(word)
    return word


async def update_adjective(
    session: AsyncSession,
    word: RandomNameAdjective,
    *,
    text: str | None = None,
    is_active: bool | None = None,
) -> RandomNameAdjective:
    if text is not None:
        normalized = text.strip()
        if not normalized:
            raise ValueError("Текст не может быть пустым")
        word.text = normalized
    if is_active is not None:
        word.is_active = is_active
    await session.commit()
    await session.refresh(word)
    return word


async def update_noun(
    session: AsyncSession,
    word: RandomNameNoun,
    *,
    text: str | None = None,
    is_active: bool | None = None,
) -> RandomNameNoun:
    if text is not None:
        normalized = text.strip()
        if not normalized:
            raise ValueError("Текст не может быть пустым")
        word.text = normalized
    if is_active is not None:
        word.is_active = is_active
    await session.commit()
    await session.refresh(word)
    return word


async def delete_adjective(session: AsyncSession, word: RandomNameAdjective) -> None:
    await session.delete(word)
    await session.commit()


async def delete_noun(session: AsyncSession, word: RandomNameNoun) -> None:
    await session.delete(word)
    await session.commit()

