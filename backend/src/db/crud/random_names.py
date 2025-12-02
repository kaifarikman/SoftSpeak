"""CRUD и утилиты для генерации случайных псевдонимов."""
from __future__ import annotations

import random
import logging
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import RandomNameAdjective, RandomNameNoun

logger = logging.getLogger(__name__)

# In-memory кэш для активных слов
_cached_adjectives: Optional[list[str]] = None
_cached_nouns: Optional[list[str]] = None

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


async def _load_active_words(session: AsyncSession, model) -> list[str]:
    """Загружает активные слова из БД."""
    stmt = select(model).where(model.is_active.is_(True))
    result = await session.execute(stmt)
    words = [obj.text for obj in result.scalars().all()]
    return words


async def _get_cached_adjectives(session: AsyncSession) -> list[str]:
    """Получает кэшированные прилагательные или загружает из БД."""
    global _cached_adjectives
    if _cached_adjectives is None:
        _cached_adjectives = await _load_active_words(session, RandomNameAdjective)
        logger.info(f"Загружено {len(_cached_adjectives)} активных прилагательных в кэш")
    return _cached_adjectives


async def _get_cached_nouns(session: AsyncSession) -> list[str]:
    """Получает кэшированные существительные или загружает из БД."""
    global _cached_nouns
    if _cached_nouns is None:
        _cached_nouns = await _load_active_words(session, RandomNameNoun)
        logger.info(f"Загружено {len(_cached_nouns)} активных существительных в кэш")
    return _cached_nouns


def _invalidate_cache():
    """Инвалидирует кэш (вызывается при изменении через админ-панель)."""
    global _cached_adjectives, _cached_nouns
    _cached_adjectives = None
    _cached_nouns = None
    logger.info("Кэш случайных имен инвалидирован")


async def _get_random_word(session: AsyncSession, model) -> str | None:
    """Получает случайное слово из кэша или БД."""
    if model == RandomNameAdjective:
        words = await _get_cached_adjectives(session)
    elif model == RandomNameNoun:
        words = await _get_cached_nouns(session)
    else:
        # Fallback на прямой запрос к БД
        stmt = (
            select(model)
            .where(model.is_active.is_(True))
            .order_by(func.random())
            .limit(1)
        )
        result = await session.execute(stmt)
        obj = result.scalar_one_or_none()
        return obj.text if obj else None
    
    if words:
        return random.choice(words)
    return None


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
    # Инвалидируем кэш при создании нового слова
    _invalidate_cache()
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
    # Инвалидируем кэш при создании нового слова
    _invalidate_cache()
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
    # Инвалидируем кэш при изменении активности
    _invalidate_cache()
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
    # Инвалидируем кэш при изменении активности
    _invalidate_cache()
    return word


async def delete_adjective(session: AsyncSession, word: RandomNameAdjective) -> None:
    await session.delete(word)
    await session.commit()
    # Инвалидируем кэш при удалении
    _invalidate_cache()


async def delete_noun(session: AsyncSession, word: RandomNameNoun) -> None:
    await session.delete(word)
    await session.commit()
    # Инвалидируем кэш при удалении
    _invalidate_cache()

