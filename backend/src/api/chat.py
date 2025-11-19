"""API эндпоинты для работы с чатами."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.crud.chat import get_chat_with_messages, get_or_create_active_chat, create_message
from src.db.crud.auth import get_user_by_username
from src.db.crud.psychological import has_completed_profile, get_user_answers_count
from src.db.session import get_db
from src.schemas.chat import ChatResponse, MessageSchema
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


async def get_chat_data_for_user(
    session: AsyncSession,
    username: str,
) -> ChatResponse:
    """
    Получает данные чата для пользователя.
    Логика:
    - Если ai_enabled = True и есть чат с сообщениями -> возвращаем массив сообщений
    - Если ai_enabled = True и чата нет -> возвращаем True (новый чат)
    - Если ai_enabled = False -> возвращаем False, messengers должен быть True
    """
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    # Если AI недоступен, возвращаем ai=False и messengers=True
    if not user.ai_enabled:
        return ChatResponse(
            ai=False,  # type: ignore
            anonym=user.anonym,
            messengers=True,  # Если AI недоступен, messengers должен быть доступен
            settings=user.settings_enabled,
            avatar=user.avatar or "",
        )

    # Получаем чат с сообщениями
    chat = await get_chat_with_messages(session, user.id)
    
    # Проверяем, есть ли сообщения от пользователя в AI чате
    has_user_messages = False
    if chat and chat.messages:
        has_user_messages = any(msg.is_from_user for msg in chat.messages)
    
    # Проверяем, завершен ли психологический профиль
    profile_completed = await has_completed_profile(session, user.id)
    answers_count = await get_user_answers_count(session, user.id)
    
    # Если профиль не завершен (новый пользователь или опрос в процессе)
    if not profile_completed:
        # Если есть сообщения в AI чате, мессенджеры уже должны быть активированы
        messengers_available = user.messengers_enabled or has_user_messages
        
        # Если есть сообщения, показываем их, иначе предлагаем начать опрос
        if has_user_messages and chat and chat.messages:
            messages = [MessageSchema.model_validate(msg) for msg in chat.messages]
            return ChatResponse(
                ai=messages,  # type: ignore
                anonym=user.anonym,
                messengers=messengers_available,
                settings=user.settings_enabled,
                avatar=user.avatar or "",
            )
        else:
            return ChatResponse(
                ai="start_survey",  # type: ignore  # Специальный флаг для начала/продолжения опроса
                anonym=user.anonym,
                messengers=messengers_available,  # Мессенджеры доступны после первого сообщения в AI чате
                settings=user.settings_enabled,
                avatar=user.avatar or "",
            )
    
    # Если чат есть и есть сообщения - возвращаем массив сообщений
    if chat and chat.messages:
        messages = [MessageSchema.model_validate(msg) for msg in chat.messages]
        return ChatResponse(
            ai=messages,  # type: ignore
            anonym=user.anonym,
            messengers=user.messengers_enabled,
            settings=user.settings_enabled,
            avatar=user.avatar or "",
        )

    # Если чата нет или он пустой - возвращаем True (новый чат)
    return ChatResponse(
        ai=True,  # type: ignore
        anonym=user.anonym,
        messengers=user.messengers_enabled,
        settings=user.settings_enabled,
        avatar=user.avatar or "",
    )


@router.get(
    "/data/{username}",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def get_chat_data(
    username: str,
    session: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Получает данные чата для указанного пользователя.
    """
    return await get_chat_data_for_user(session, username)


class SendMessageRequest(BaseModel):
    text: str


@router.post(
    "/message/{username}",
    response_model=MessageSchema,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    username: str,
    request: SendMessageRequest,
    session: AsyncSession = Depends(get_db),
) -> MessageSchema:
    """
    Отправляет сообщение в AI чат пользователя.
    После первого сообщения активирует мессенджеры.
    """
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    # Проверяем, доступен ли AI чат
    if not user.ai_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI чат недоступен",
        )
    
    # Получаем или создаем активный чат
    chat = await get_or_create_active_chat(session, user.id)
    
    # Создаем сообщение от пользователя
    message = await create_message(
        session,
        chat.id,
        request.text,
        is_from_user=True,
    )
    
    # После создания сообщения мессенджеры должны быть активированы автоматически
    # (это происходит в create_message)
    
    return MessageSchema.model_validate(message)

