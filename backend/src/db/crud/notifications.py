from __future__ import annotations
from typing import Optional
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.db.models import User, AnonymousChat, AnonymousMessage


async def get_unread_notifications(session: AsyncSession, user_id: int) -> list[dict]:
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if not user:
        return []
    notifications = []
    if user.notification_anon_chats:
        anon_chats_stmt = (
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
            .options(selectinload(AnonymousChat.messages))
        )
        anon_chats_result = await session.execute(anon_chats_stmt)
        anon_chats = anon_chats_result.scalars().all()
        for chat in anon_chats:
            if chat.user1_id == user_id:
                other_alias = chat.user2_alias
            else:
                other_alias = chat.user1_alias
            chat_name = other_alias or "Собеседник"
            unread_messages = [
                msg
                for msg in chat.messages
                if msg.sender_id != user_id and (not msg.is_read)
            ]
            if unread_messages:
                last_message = max(unread_messages, key=lambda m: m.created_at)
                unread_count = len(unread_messages)
                notifications.append(
                    {
                        "chat_id": chat.id,
                        "chat_name": chat_name,
                        "chat_type": "anon",
                        "unread_count": unread_count,
                        "last_message": (
                            last_message.content[:100] if last_message.content else ""
                        ),
                        "last_message_time": last_message.created_at.isoformat(),
                    }
                )
    if user.notification_open_chats:
        public_chats_stmt = (
            select(AnonymousChat, User)
            .join(
                User,
                or_(
                    and_(
                        AnonymousChat.user1_id == user_id,
                        User.id == AnonymousChat.user2_id,
                    ),
                    and_(
                        AnonymousChat.user2_id == user_id,
                        User.id == AnonymousChat.user1_id,
                    ),
                ),
            )
            .where(
                and_(
                    or_(
                        AnonymousChat.user1_id == user_id,
                        AnonymousChat.user2_id == user_id,
                    ),
                    AnonymousChat.is_active.is_(True),
                    AnonymousChat.is_public.is_(True),
                )
            )
            .options(selectinload(AnonymousChat.messages))
        )
        public_chats_result = await session.execute(public_chats_stmt)
        public_chats_data = public_chats_result.all()
        for chat, other_user in public_chats_data:
            chat_name = other_user.nickname if other_user else "Собеседник"
            unread_messages = [
                msg
                for msg in chat.messages
                if msg.sender_id != user_id and (not msg.is_read)
            ]
            if unread_messages:
                last_message = max(unread_messages, key=lambda m: m.created_at)
                unread_count = len(unread_messages)
                notifications.append(
                    {
                        "chat_id": chat.id,
                        "chat_name": chat_name,
                        "chat_type": "people",
                        "unread_count": unread_count,
                        "last_message": (
                            last_message.content[:100] if last_message.content else ""
                        ),
                        "last_message_time": last_message.created_at.isoformat(),
                    }
                )
    notifications.sort(key=lambda x: x["last_message_time"], reverse=True)
    return notifications
