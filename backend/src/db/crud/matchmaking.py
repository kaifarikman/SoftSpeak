"""CRUD-операции для матчинга и анонимных чатов."""
from typing import Optional
from datetime import datetime, timezone
import logging

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import (
    MatchmakingQueue,
    AnonymousChat,
    AnonymousMessage,
    User,
    PsychologicalProfile,
)
from src.db.crud import random_names
from src.services.vector_utils import find_best_match

logger = logging.getLogger(__name__)


def summarize_message_text(message: AnonymousMessage) -> str:
    if message.media_type == "photo":
        return "📷 Фото"
    if message.media_type == "video":
        return "🎬 Видео"
    content = (message.content or "").strip()
    if not content:
        return "Сообщение"
    return content[:50]


async def join_matchmaking_queue(
    session: AsyncSession,
    user_id: int,
) -> MatchmakingQueue:
    """
    Добавляет пользователя в очередь матчинга или обновляет существующую запись.
    """
    stmt = select(MatchmakingQueue).where(MatchmakingQueue.user_id == user_id)
    result = await session.execute(stmt)
    queue_entry = result.scalar_one_or_none()

    if queue_entry:
        # Обновляем существующую запись
        queue_entry.is_searching = True
        queue_entry.joined_at = datetime.now(timezone.utc)
    else:
        # Создаем новую запись
        queue_entry = MatchmakingQueue(
            user_id=user_id,
            is_searching=True,
        )
        session.add(queue_entry)

    await session.commit()
    await session.refresh(queue_entry)
    logger.info(f"join_matchmaking_queue: Пользователь {user_id} успешно добавлен/обновлен в очереди")
    return queue_entry


async def leave_matchmaking_queue(
    session: AsyncSession,
    user_id: int,
) -> bool:
    """
    Удаляет пользователя из очереди матчинга.
    """
    stmt = select(MatchmakingQueue).where(MatchmakingQueue.user_id == user_id)
    result = await session.execute(stmt)
    queue_entry = result.scalar_one_or_none()

    if queue_entry:
        await session.delete(queue_entry)
        await session.commit()
        logger.info(f"leave_matchmaking_queue: Пользователь {user_id} удален из очереди")
        return True
    logger.info(f"leave_matchmaking_queue: Пользователь {user_id} не был в очереди")
    return False


async def get_matchmaking_queue_count(
    session: AsyncSession,
    exclude_user_id: Optional[int] = None,
) -> int:
    """
    Получает количество пользователей в очереди матчинга.
    """
    stmt = select(func.count(MatchmakingQueue.id)).where(
        MatchmakingQueue.is_searching.is_(True)
    )
    
    if exclude_user_id:
        stmt = stmt.where(MatchmakingQueue.user_id != exclude_user_id)
    
    result = await session.execute(stmt)
    return result.scalar() or 0


async def find_match(
    session: AsyncSession,
    user_id: int,
) -> Optional[AnonymousChat]:
    """
    Ищет матч для пользователя.
    Возвращает созданный чат или None, если матч не найден.
    Использует SELECT FOR UPDATE для предотвращения race conditions.
    """
    # Получаем текущего пользователя с профилем
    user_stmt = (
        select(User)
        .options(selectinload(User.psychological_profile))
        .where(User.id == user_id)
    )
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if not user:
        logger.warning(f"find_match: Пользователь {user_id} не найден")
        return None
    
    if not user.messengers_enabled:
        logger.warning(f"find_match: У пользователя {user_id} отключены мессенджеры")
        return None

    # Получаем профиль пользователя
    if not user.psychological_profile:
        logger.warning(f"find_match: У пользователя {user_id} нет психологического профиля")
        return None

    user_vector = user.psychological_profile.profile_vector
    logger.info(f"find_match: Начинаем поиск матча для пользователя {user_id}")

    # Получаем всех пользователей в очереди, кроме текущего
    # Используем FOR UPDATE SKIP LOCKED для предотвращения блокировок
    queue_stmt = (
        select(MatchmakingQueue)
        .where(
            and_(
                MatchmakingQueue.is_searching.is_(True),
                MatchmakingQueue.user_id != user_id,
            )
        )
        .options(selectinload(MatchmakingQueue.user).selectinload(User.psychological_profile))
        .with_for_update(skip_locked=True)
    )
    queue_result = await session.execute(queue_stmt)
    queue_entries = queue_result.scalars().all()

    if not queue_entries:
        logger.info(f"find_match: Нет других пользователей в очереди для {user_id}")
        return None
    
    logger.info(f"find_match: Найдено {len(queue_entries)} пользователей в очереди")

    # Формируем список других пользователей с их профилями
    other_users = []
    for entry in queue_entries:
        if entry.user and entry.user.psychological_profile and entry.user.messengers_enabled:
            other_users.append({
                'id': entry.user.id,
                'profile_vector': entry.user.psychological_profile.profile_vector,
            })

    if not other_users:
        logger.info(f"find_match: Нет подходящих пользователей с профилями для {user_id}")
        return None

    logger.info(f"find_match: Ищем лучший матч среди {len(other_users)} пользователей")
    
    # Ищем лучший матч
    best_match_id = await find_best_match(
        user_vector=user_vector,
        user_id=user_id,
        other_users=other_users,
    )

    if not best_match_id:
        logger.warning(f"find_match: Не удалось найти лучший матч для {user_id}")
        return None
    
    logger.info(f"find_match: Найден лучший матч для {user_id}: пользователь {best_match_id}")

    # Проверяем, нет ли уже активного чата между этими пользователями
    existing_chat_stmt = select(AnonymousChat).where(
        or_(
            and_(
                AnonymousChat.user1_id == user_id,
                AnonymousChat.user2_id == best_match_id,
            ),
            and_(
                AnonymousChat.user1_id == best_match_id,
                AnonymousChat.user2_id == user_id,
            ),
        ),
        AnonymousChat.is_active.is_(True),
    )
    existing_chat_result = await session.execute(existing_chat_stmt)
    existing_chat = existing_chat_result.scalar_one_or_none()

    if existing_chat:
        logger.info(f"find_match: Уже существует чат {existing_chat.id} между {user_id} и {best_match_id}")
        # Удаляем обоих пользователей из очереди (в текущей сессии)
        stmt1 = select(MatchmakingQueue).where(MatchmakingQueue.user_id == user_id)
        result1 = await session.execute(stmt1)
        entry1 = result1.scalar_one_or_none()
        if entry1:
            await session.delete(entry1)
        
        stmt2 = select(MatchmakingQueue).where(MatchmakingQueue.user_id == best_match_id)
        result2 = await session.execute(stmt2)
        entry2 = result2.scalar_one_or_none()
        if entry2:
            await session.delete(entry2)
        
        await session.commit()
        return existing_chat

    # Создаем новый чат
    # user1_id всегда меньше user2_id для консистентности
    user1_id_sorted, user2_id_sorted = (user_id, best_match_id) if user_id < best_match_id else (best_match_id, user_id)

    # Еще раз проверяем на наличие чата (защита от race condition)
    check_stmt = select(AnonymousChat).where(
        and_(
            AnonymousChat.user1_id == user1_id_sorted,
            AnonymousChat.user2_id == user2_id_sorted,
            AnonymousChat.is_active.is_(True),
        )
    ).with_for_update()
    
    check_result = await session.execute(check_stmt)
    final_check_chat = check_result.scalar_one_or_none()
    
    if final_check_chat:
        # Чат уже создан другим пользователем (race condition предотвращена)
        logger.info(f"find_match: Чат {final_check_chat.id} уже был создан (race condition), возвращаем существующий")
        # Удаляем из очереди
        stmt1 = select(MatchmakingQueue).where(MatchmakingQueue.user_id == user_id)
        result1 = await session.execute(stmt1)
        entry1 = result1.scalar_one_or_none()
        if entry1:
            await session.delete(entry1)
        
        stmt2 = select(MatchmakingQueue).where(MatchmakingQueue.user_id == best_match_id)
        result2 = await session.execute(stmt2)
        entry2 = result2.scalar_one_or_none()
        if entry2:
            await session.delete(entry2)
        
        await session.commit()
        return final_check_chat

    # Создаем чат
    chat = AnonymousChat(
        user1_id=user1_id_sorted,
        user2_id=user2_id_sorted,
        is_active=True,
    )
    chat.user1_alias = await random_names.generate_random_alias(session)
    chat.user2_alias = await random_names.generate_random_alias(session)
    session.add(chat)

    # Удаляем обоих пользователей из очереди
    stmt1 = select(MatchmakingQueue).where(MatchmakingQueue.user_id == user_id)
    result1 = await session.execute(stmt1)
    entry1 = result1.scalar_one_or_none()
    if entry1:
        await session.delete(entry1)
    
    stmt2 = select(MatchmakingQueue).where(MatchmakingQueue.user_id == best_match_id)
    result2 = await session.execute(stmt2)
    entry2 = result2.scalar_one_or_none()
    if entry2:
        await session.delete(entry2)

    await session.commit()
    await session.refresh(chat)

    logger.info(f"find_match: Успешно создан новый чат {chat.id} между {user_id} и {best_match_id}")
    return chat


async def get_user_anonymous_chats(
    session: AsyncSession,
    user_id: int,
) -> list[AnonymousChat]:
    """
    Получает все активные анонимные чаты пользователя.
    """
    stmt = (
        select(AnonymousChat)
        .where(
            and_(
                or_(
                    AnonymousChat.user1_id == user_id,
                    AnonymousChat.user2_id == user_id,
                ),
                AnonymousChat.is_active.is_(True),
                AnonymousChat.is_public.is_(False),
            )
        )
        .options(
            selectinload(AnonymousChat.user1),
            selectinload(AnonymousChat.user2),
            selectinload(AnonymousChat.messages),
        )
        .order_by(AnonymousChat.updated_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_anonymous_chat(
    session: AsyncSession,
    chat_id: int,
    user_id: int,
) -> Optional[AnonymousChat]:
    """
    Получает анонимный чат по ID, если пользователь является участником.
    """
    stmt = (
        select(AnonymousChat)
        .where(
            and_(
                AnonymousChat.id == chat_id,
                or_(
                    AnonymousChat.user1_id == user_id,
                    AnonymousChat.user2_id == user_id,
                ),
            )
        )
        .options(
            selectinload(AnonymousChat.user1),
            selectinload(AnonymousChat.user2),
            selectinload(AnonymousChat.messages),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_anonymous_message(
    session: AsyncSession,
    chat_id: int,
    sender_id: int,
    content: str | None = None,
    *,
    media_type: str | None = None,
    media_url: str | None = None,
    media_preview_url: str | None = None,
    media_size: int | None = None,
    media_duration: float | None = None,
    media_width: int | None = None,
    media_height: int | None = None,
) -> AnonymousMessage:
    """
    Создает сообщение в анонимном чате.
    """
    # Проверяем, что отправитель является участником чата
    chat_stmt = select(AnonymousChat).where(AnonymousChat.id == chat_id)
    chat_result = await session.execute(chat_stmt)
    chat = chat_result.scalar_one_or_none()

    if not chat:
        raise ValueError("Чат не найден")

    if chat.user1_id != sender_id and chat.user2_id != sender_id:
        raise ValueError("Пользователь не является участником чата")

    message = AnonymousMessage(
        chat_id=chat_id,
        sender_id=sender_id,
        content=(content or ""),
        media_type=media_type,
        media_url=media_url,
        media_preview_url=media_preview_url,
        media_size=media_size,
        media_duration=media_duration,
        media_width=media_width,
        media_height=media_height,
    )
    session.add(message)

    # Обновляем updated_at чата
    chat.updated_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(message)
    return message


async def get_user_public_chats(
    session: AsyncSession,
    user_id: int,
) -> list[AnonymousChat]:
    """
    Получает все раскрытые (публичные) чаты пользователя.
    """
    stmt = (
        select(AnonymousChat)
        .where(
            and_(
                or_(
                    AnonymousChat.user1_id == user_id,
                    AnonymousChat.user2_id == user_id,
                ),
                AnonymousChat.is_public.is_(True),
                AnonymousChat.is_active.is_(True),
            )
        )
        .options(
            selectinload(AnonymousChat.user1),
            selectinload(AnonymousChat.user2),
            selectinload(AnonymousChat.messages),
        )
        .order_by(AnonymousChat.updated_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def reveal_anonymous_chat(
    session: AsyncSession,
    chat_id: int,
    user_id: int,
) -> tuple[AnonymousChat, bool]:
    """
    Отмечает желание пользователя раскрыться.
    Если оба пользователя согласны, переводит чат в публичный.
    Возвращает кортеж (chat, both_revealed), где both_revealed = True, если оба согласны.
    """
    chat = await get_anonymous_chat(session, chat_id, user_id)
    if not chat:
        raise ValueError("Чат не найден")

    if chat.is_public:
        # Чат уже публичный
        return chat, True

    # Определяем, кто из пользователей хочет раскрыться
    if chat.user1_id == user_id:
        if not chat.user1_revealed:
            chat.user1_revealed = True
    elif chat.user2_id == user_id:
        if not chat.user2_revealed:
            chat.user2_revealed = True
    else:
        raise ValueError("Пользователь не является участником чата")

    # Проверяем, хотят ли оба раскрыться
    both_revealed = chat.user1_revealed and chat.user2_revealed

    if both_revealed:
        # Оба согласны - переводим чат в публичный
        chat.is_public = True
        chat.revealed_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(chat)

    return chat, both_revealed

