import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.crud.psychological import (
    create_psychological_profile,
    get_psychological_profile,
    get_user_answers,
)
from src.db.session import AsyncSessionLocal
from src.services.vector_utils import create_embedding, create_profile_vector

logger = logging.getLogger(__name__)

_pending_profiles_queue: List[Tuple[int, str, datetime]] = []
_queue_lock: Optional[asyncio.Lock] = None
_retry_task = None


def _get_queue_lock() -> asyncio.Lock:
    global _queue_lock
    if _queue_lock is None:
        _queue_lock = asyncio.Lock()
    return _queue_lock


async def _retry_pending_profiles():
    global _pending_profiles_queue
    while True:
        await asyncio.sleep(60)
        if not _pending_profiles_queue:
            continue
        async with _get_queue_lock():
            queue_copy = _pending_profiles_queue.copy()
            _pending_profiles_queue.clear()
        for user_id, email, timestamp in queue_copy:
            try:
                async with AsyncSessionLocal() as session:
                    profile_created = await create_profile_with_embeddings(
                        session, user_id, email
                    )
                    if profile_created:
                        logger.info(f"✓ Отложенный профиль успешно создан для {email}")
                    elif (
                        datetime.now(timezone.utc) - timestamp
                    ).total_seconds() < 3600:
                        async with _get_queue_lock():
                            _pending_profiles_queue.append((user_id, email, timestamp))
            except Exception as e:
                logger.error(
                    f"Ошибка при обработке отложенного профиля для {email}: {e}"
                )
                if (datetime.now(timezone.utc) - timestamp).total_seconds() < 3600:
                    async with _get_queue_lock():
                        _pending_profiles_queue.append((user_id, email, timestamp))


def start_retry_task():
    global _retry_task
    if _retry_task is None or _retry_task.done():
        _retry_task = asyncio.create_task(_retry_pending_profiles())
        logger.info("Запущена фоновая задача для обработки отложенных профилей")


async def create_profile_with_embeddings(
    session: AsyncSession, user_id: int, email: str
) -> bool:
    try:
        logger.info(f"Начало создания профиля для {email}")
        answers = await get_user_answers(session, user_id)
        if len(answers) < 10:
            logger.error(
                f"Недостаточно ответов для создания профиля: {len(answers)}/10"
            )
            return False
        logger.info(f"Создание эмбеддингов для {len(answers)} ответов...")
        embeddings_created = 0
        embeddings = []
        for answer in answers:
            try:
                if not answer.embedding:
                    logger.info(f"Создание эмбеддинга для ответа {answer.id}...")
                    embedding_list = await create_embedding(answer.answer_text)
                    answer.embedding = embedding_list
                    session.add(answer)
                    embeddings.append(embedding_list)
                    embeddings_created += 1
                    logger.info(
                        f"Эмбеддинг создан ({embeddings_created}/{len(answers)})"
                    )
                else:
                    embeddings.append(answer.embedding)
            except RuntimeError as e:
                error_msg = str(e).lower()
                if (
                    "ml сервис" in error_msg
                    or "не удалось подключиться" in error_msg
                    or "недоступен" in error_msg
                ):
                    logger.warning(
                        f"ML-сервис недоступен для ответа {answer.id}, добавляем в очередь"
                    )
                    async with _get_queue_lock():
                        _pending_profiles_queue.append(
                            (user_id, email, datetime.now(timezone.utc))
                        )
                    start_retry_task()
                    return False
                else:
                    logger.error(
                        f"Ошибка создания эмбеддинга для ответа {answer.id}: {e}",
                        exc_info=True,
                    )
                    return False
            except Exception as e:
                logger.error(
                    f"Ошибка создания эмбеддинга для ответа {answer.id}: {e}",
                    exc_info=True,
                )
                return False
        await session.commit()
        logger.info(f"Все эмбеддинги созданы для {email}")
        if len(embeddings) >= 10:
            logger.info(f"Создание вектора профиля для {email}...")
            profile_vector = await create_profile_vector(embeddings)
            old_profile = await get_psychological_profile(session, user_id)
            if old_profile:
                await session.delete(old_profile)
            await create_psychological_profile(session, user_id, profile_vector)
            await session.commit()
            logger.info(f"✓ Профиль успешно создан для {email}")
            return True
        else:
            logger.error(f"Недостаточно эмбеддингов: {len(embeddings)}/10")
            return False
    except Exception as e:
        logger.error(f"Ошибка создания профиля для {email}: {e}", exc_info=True)
        return False
