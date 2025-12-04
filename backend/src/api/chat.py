from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.crud.chat import get_chat_with_messages, get_or_create_active_chat, create_message
from src.db.crud.auth import get_user_by_email
from src.db.crud.psychological import has_completed_profile, get_user_answers_count
from src.db.session import get_db
from src.schemas.chat import ChatResponse, MessageSchema
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


async def get_chat_data_for_user(
    session: AsyncSession,
    email: str,
) -> ChatResponse:
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    # Проверяем, не забанен ли пользователь
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован администратором. Доступ запрещен.",
        )

    chat = await get_chat_with_messages(session, user.id)
    
    has_user_messages = False
    if chat and chat.messages:
        has_user_messages = any(msg.is_from_user for msg in chat.messages)
    
    profile_completed = await has_completed_profile(session, user.id)
    answers_count = await get_user_answers_count(session, user.id)
    
    # Если AI отключен (после завершения опроса), возвращаем историю для просмотра, но отправка будет заблокирована
    if not user.ai_enabled:
        # Если есть история и профиль завершен, показываем ее для просмотра
        if chat and chat.messages and profile_completed:
            messages = [MessageSchema.model_validate(msg) for msg in chat.messages]
            # Возвращаем массив сообщений для просмотра, но фронтенд должен блокировать отправку
            return ChatResponse(
                ai=messages,  # История для просмотра
                anonym=user.anonym,
                messengers=user.messengers_enabled,
                settings=user.settings_enabled,
            )
        # Если истории нет или профиль не завершен, возвращаем ai=False
        return ChatResponse(
            ai=False,  # AI недоступен
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
    
    # Профиль завершен, но ai_enabled еще True (старые пользователи)
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
    "/data/{email}",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def get_chat_data(
    email: str,
    session: AsyncSession = Depends(get_db),
) -> ChatResponse:
    return await get_chat_data_for_user(session, email)


class SendMessageRequest(BaseModel):
    text: str


@router.post(
    "/message/{email}",
    response_model=MessageSchema,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    email: str,
    request: SendMessageRequest,
    session: AsyncSession = Depends(get_db),
) -> MessageSchema:
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован администратором. Доступ запрещен.",
        )
    
    if not user.ai_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI чат недоступен",
        )
    
    chat = await get_or_create_active_chat(session, user.id)
    
    message = await create_message(
        session,
        chat.id,
        request.text,
        is_from_user=True,
    )
    
    return MessageSchema.model_validate(message)

