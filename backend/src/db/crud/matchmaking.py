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
    Blacklist,
)
from src.db.crud import random_names
from src.services.vector_utils import find_best_match

logger = logging.getLogger(__name__)


def summarize_message_text(message: AnonymousMessage) -> str:
    content = (message.content or "").strip()
    if not content:
        return "Сообщение"
    return content[:50]


async def join_matchmaking_queue(
    session: AsyncSession,
    user_id: int,
) -> MatchmakingQueue:
    stmt = select(MatchmakingQueue).where(MatchmakingQueue.user_id == user_id)
    result = await session.execute(stmt)
    queue_entry = result.scalar_one_or_none()

    if queue_entry:
        queue_entry.is_searching = True
        queue_entry.joined_at = datetime.now(timezone.utc)
    else:
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
    
    if not user.psychological_profile:
        logger.warning(f"find_match: У пользователя {user_id} нет психологического профиля")
        return None

    user_vector = user.psychological_profile.profile_vector
    logger.info(f"find_match: Начинаем поиск матча для пользователя {user_id}")
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

    blocked_by_user_stmt = select(Blacklist.blocked_user_id).where(
        Blacklist.user_id == user_id
    )
    blocked_by_user_result = await session.execute(blocked_by_user_stmt)
    blocked_by_user_ids = {row[0] for row in blocked_by_user_result.all()}
    
    blocked_user_stmt = select(Blacklist.user_id).where(
        Blacklist.blocked_user_id == user_id
    )
    blocked_user_result = await session.execute(blocked_user_stmt)
    blocked_user_ids = {row[0] for row in blocked_user_result.all()}
    
    all_blocked_ids = blocked_by_user_ids | blocked_user_ids
    
    if all_blocked_ids:
        logger.info(f"find_match: Исключаем {len(all_blocked_ids)} заблокированных пользователей для {user_id}")

    other_users = []
    for entry in queue_entries:
        if entry.user.id in all_blocked_ids:
            logger.debug(f"find_match: Пропускаем пользователя {entry.user.id} - он в черном списке")
            continue
            
        if entry.user and entry.user.psychological_profile and entry.user.messengers_enabled:
            other_users.append({
                'id': entry.user.id,
                'profile_vector': entry.user.psychological_profile.profile_vector,
            })

    if not other_users:
        logger.info(f"find_match: Нет подходящих пользователей с профилями для {user_id}")
        return None

    logger.info(f"find_match: Ищем лучший матч среди {len(other_users)} пользователей")
    
    best_match_id = await find_best_match(
        user_vector=user_vector,
        user_id=user_id,
        other_users=other_users,
    )

    if not best_match_id:
        logger.warning(f"find_match: Не удалось найти лучший матч для {user_id}")
        return None
    
    logger.info(f"find_match: Найден лучший матч для {user_id}: пользователь {best_match_id}")

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

    user1_id_sorted, user2_id_sorted = (user_id, best_match_id) if user_id < best_match_id else (best_match_id, user_id)
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
        logger.info(f"find_match: Чат {final_check_chat.id} уже был создан (race condition), возвращаем существующий")
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

    chat = AnonymousChat(
        user1_id=user1_id_sorted,
        user2_id=user2_id_sorted,
        is_active=True,
    )
    
    max_attempts = 10
    user1_alias = await random_names.generate_random_alias(session)
    user2_alias = await random_names.generate_random_alias(session)
    
    attempts = 0
    while user1_alias == user2_alias and attempts < max_attempts:
        logger.warning(f"find_match: Алиасы совпали ({user1_alias}), перегенерируем user2_alias")
        user2_alias = await random_names.generate_random_alias(session)
        attempts += 1
    
    if user1_alias == user2_alias:
        logger.error(f"find_match: Не удалось сгенерировать уникальные алиасы после {max_attempts} попыток")
        user2_alias = f"{user2_alias} 2"
    
    chat.user1_alias = user1_alias
    chat.user2_alias = user2_alias
    session.add(chat)

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
) -> AnonymousMessage:
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
    )
    session.add(message)

    chat.updated_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(message)
    return message


async def get_user_public_chats(
    session: AsyncSession,
    user_id: int,
) -> list[AnonymousChat]:
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


async def mark_messages_as_read(
    session: AsyncSession,
    chat_id: int,
    user_id: int,
) -> int:
    chat = await get_anonymous_chat(session, chat_id, user_id)
    if not chat:
        raise ValueError("Чат не найден")
    
    unread_messages = [
        msg for msg in chat.messages 
        if msg.sender_id != user_id and not msg.is_read
    ]
    
    count = 0
    for message in unread_messages:
        message.is_read = True
        count += 1
    
    if count > 0:
        await session.commit()
        logger.info(f"mark_messages_as_read: Помечено {count} сообщений как прочитанных в чате {chat_id} для пользователя {user_id}")
    
    return count


async def reveal_anonymous_chat(
    session: AsyncSession,
    chat_id: int,
    user_id: int,
) -> tuple[AnonymousChat, bool]:
    chat = await get_anonymous_chat(session, chat_id, user_id)
    if not chat:
        raise ValueError("Чат не найден")

    if chat.is_public:
        return chat, True

    if chat.user1_id == user_id:
        if not chat.user1_revealed:
            chat.user1_revealed = True
    elif chat.user2_id == user_id:
        if not chat.user2_revealed:
            chat.user2_revealed = True
    else:
        raise ValueError("Пользователь не является участником чата")

    both_revealed = chat.user1_revealed and chat.user2_revealed

    if both_revealed:
        chat.is_public = True
        chat.revealed_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(chat)

    return chat, both_revealed

