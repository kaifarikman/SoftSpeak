from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.crud.chat import (
    get_chat_with_messages,
    get_or_create_active_chat,
    create_message,
)
from src.db.crud.auth import get_user_by_email
from src.db.crud.matchmaking import (
    get_user_anonymous_chats,
    get_user_public_chats,
    summarize_message_text,
)
from src.db.crud.psychological import has_completed_profile, get_user_answers_count
from src.db.session import get_db
from src.schemas.chat import ChatResponse, MessageSchema
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


async def get_chat_data_for_user(session: AsyncSession, email: str) -> ChatResponse:
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован администратором. Доступ запрещен.",
        )
    chat = await get_chat_with_messages(session, user.id)
    has_user_messages = False
    if chat and chat.messages:
        has_user_messages = any((msg.is_from_user for msg in chat.messages))
    profile_completed = await has_completed_profile(session, user.id)
    answers_count = await get_user_answers_count(session, user.id)
    if not user.ai_enabled:
        if chat and chat.messages and profile_completed:
            messages = [MessageSchema.model_validate(msg) for msg in chat.messages]
            return ChatResponse(
                ai=messages,
                anonym=user.anonym,
                messengers=user.messengers_enabled,
                settings=user.settings_enabled,
            )
        return ChatResponse(
            ai=False,
            anonym=user.anonym,
            messengers=user.messengers_enabled,
            settings=user.settings_enabled,
        )
    if not profile_completed:
        messengers_available = user.messengers_enabled or has_user_messages
        if has_user_messages and chat and chat.messages:
            messages = [MessageSchema.model_validate(msg) for msg in chat.messages]
            return ChatResponse(
                ai=messages,
                anonym=user.anonym,
                messengers=messengers_available,
                settings=user.settings_enabled,
            )
        else:
            return ChatResponse(
                ai="start_survey",
                anonym=user.anonym,
                messengers=messengers_available,
                settings=user.settings_enabled,
            )
    if chat and chat.messages:
        messages = [MessageSchema.model_validate(msg) for msg in chat.messages]
        return ChatResponse(
            ai=messages,
            anonym=user.anonym,
            messengers=user.messengers_enabled,
            settings=user.settings_enabled,
        )
    return ChatResponse(
        ai=True,
        anonym=user.anonym,
        messengers=user.messengers_enabled,
        settings=user.settings_enabled,
    )


@router.get(
    "/data/{email}", response_model=ChatResponse, status_code=status.HTTP_200_OK
)
async def get_chat_data(
    email: str, session: AsyncSession = Depends(get_db)
) -> ChatResponse:
    return await get_chat_data_for_user(session, email)


class SendMessageRequest(BaseModel):
    text: str


@router.get("/search", status_code=status.HTTP_200_OK)
async def search_chats(
    email: str,
    q: str = Query("", max_length=128),
    limit: int = Query(20, ge=1, le=50),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован администратором. Доступ запрещен.",
        )

    query = q.strip().lower()
    results = []
    if not query or "softspeak".lower().startswith(query):
        results.append({"id": "bot", "type": "bot", "name": "SoftSpeak"})

    for chat_type, chats in (
        ("anon", await get_user_anonymous_chats(session, user.id)),
        ("people", await get_user_public_chats(session, user.id)),
    ):
        for chat in chats:
            other_user = chat.user2 if chat.user1_id == user.id else chat.user1
            if chat_type == "people":
                name = other_user.nickname
            else:
                name = chat.user2_alias if chat.user1_id == user.id else chat.user1_alias
                name = name or "Собеседник"
            last_message = summarize_message_text(chat.messages[-1]) if chat.messages else ""
            haystack = f"{name} {last_message}".lower()
            if query and query not in haystack:
                continue
            results.append(
                {
                    "id": chat.id,
                    "type": chat_type,
                    "name": name,
                    "last_message": last_message,
                    "updated_at": chat.updated_at.isoformat(),
                }
            )
            if len(results) >= limit:
                return results
    return results[:limit]


@router.post(
    "/message/{email}",
    response_model=MessageSchema,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    email: str, request: SendMessageRequest, session: AsyncSession = Depends(get_db)
) -> MessageSchema:
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован администратором. Доступ запрещен.",
        )
    if not user.ai_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="AI чат недоступен"
        )
    chat = await get_or_create_active_chat(session, user.id)
    message = await create_message(session, chat.id, request.text, is_from_user=True)
    return MessageSchema.model_validate(message)
