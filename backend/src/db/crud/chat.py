"""CRUD-операции для работы с чатами и сообщениями."""
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import Chat, Message, User


async def get_or_create_active_chat(
    session: AsyncSession,
    user_id: int,
) -> Chat:
    """
    Получает активный чат пользователя или создает новый, если его нет.
    """
    stmt = (
        select(Chat)
        .where(Chat.user_id == user_id, Chat.is_active.is_(True))
        .options(selectinload(Chat.messages))
        .order_by(Chat.created_at.desc())
    )
    result = await session.execute(stmt)
    chat = result.scalar_one_or_none()

    if not chat:
        chat = Chat(user_id=user_id, is_active=True)
        session.add(chat)
        await session.commit()
        await session.refresh(chat)
        # Загружаем сообщения для нового чата
        await session.refresh(chat, ["messages"])

    return chat


async def get_chat_with_messages(
    session: AsyncSession,
    user_id: int,
) -> Optional[Chat]:
    """
    Получает активный чат пользователя со всеми сообщениями.
    """
    stmt = (
        select(Chat)
        .where(Chat.user_id == user_id, Chat.is_active.is_(True))
        .options(selectinload(Chat.messages))
        .order_by(Chat.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_message(
    session: AsyncSession,
    chat_id: int,
    content: str,
    is_from_user: bool = True,
) -> Message:
    """
    Создает новое сообщение в чате.
    Если это первое сообщение от пользователя, активирует мессенджеры.
    """
    message = Message(
        chat_id=chat_id,
        content=content,
        is_from_user=is_from_user,
    )
    session.add(message)
    
    # Если это сообщение от пользователя, проверяем, нужно ли активировать мессенджеры
    if is_from_user:
        # Получаем чат и пользователя
        stmt = select(Chat).where(Chat.id == chat_id)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if chat:
            # Получаем пользователя
            user_stmt = select(User).where(User.id == chat.user_id)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if user and not user.messengers_enabled:
                # Проверяем, есть ли уже сообщения от пользователя в этом чате
                messages_stmt = select(func.count(Message.id)).where(
                    Message.chat_id == chat_id,
                    Message.is_from_user.is_(True)
                )
                messages_result = await session.execute(messages_stmt)
                user_messages_count = messages_result.scalar() or 0
                
                # Если это первое сообщение от пользователя, активируем мессенджеры
                if user_messages_count == 0:  # До добавления текущего сообщения
                    user.messengers_enabled = True
    
    await session.commit()
    await session.refresh(message)
    return message

