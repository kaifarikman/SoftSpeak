"""API эндпоинты для матчинга и анонимных чатов."""
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict
import json
import logging
import asyncio

from src.db.session import get_db, AsyncSessionLocal
from src.db.crud.auth import get_user_by_username
from src.db.crud.matchmaking import (
    join_matchmaking_queue,
    leave_matchmaking_queue,
    get_matchmaking_queue_count,
    find_match,
    get_user_anonymous_chats,
    get_user_public_chats,
    get_anonymous_chat,
    create_anonymous_message,
    reveal_anonymous_chat,
)
from src.db.crud.psychological import has_completed_profile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/matchmaking", tags=["matchmaking"])


class MatchmakingStatusResponse(BaseModel):
    """Ответ со статусом матчинга."""
    is_searching: bool
    queue_count: int
    chat_id: int | None = None


class AnonymousChatSchema(BaseModel):
    """Схема анонимного чата."""
    id: int
    user1_id: int
    user2_id: int
    created_at: str
    updated_at: str
    last_message: str | None = None
    last_message_time: str | None = None
    unread_count: int = 0

    class Config:
        from_attributes = True


class AnonymousMessageSchema(BaseModel):
    """Схема сообщения в анонимном чате."""
    id: int
    content: str
    sender_id: int
    is_mine: bool
    created_at: str

    class Config:
        from_attributes = True


class SendAnonymousMessageRequest(BaseModel):
    """Запрос на отправку сообщения."""
    text: str


# WebSocket менеджер для матчинга
class MatchmakingConnectionManager:
    """Менеджер WebSocket соединений для матчинга."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.searching_users: Dict[str, asyncio.Task] = {}  # username -> поисковая задача

    async def connect(self, websocket: WebSocket, username: str):
        """Подключает пользователя."""
        await websocket.accept()
        self.active_connections[username] = websocket

    def disconnect(self, username: str):
        """Отключает пользователя."""
        if username in self.active_connections:
            del self.active_connections[username]
        # Останавливаем поисковую задачу
        if username in self.searching_users:
            self.searching_users[username].cancel()
            del self.searching_users[username]

    async def send_personal_message(self, message: dict, username: str):
        """Отправляет сообщение конкретному пользователю."""
        if username in self.active_connections:
            websocket = self.active_connections[username]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения через WebSocket для пользователя {username}: {e}")
                self.disconnect(username)


matchmaking_manager = MatchmakingConnectionManager()


# WebSocket менеджер для анонимных чатов
class AnonymousChatConnectionManager:
    """Менеджер WebSocket соединений для анонимных чатов."""

    def __init__(self):
        # chat_id -> {username: WebSocket}
        self.chat_connections: Dict[int, Dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, chat_id: int, username: str):
        """Подключает пользователя к чату."""
        await websocket.accept()
        if chat_id not in self.chat_connections:
            self.chat_connections[chat_id] = {}
        self.chat_connections[chat_id][username] = websocket
        logger.info(f"Пользователь {username} подключился к чату {chat_id}")

    def disconnect(self, chat_id: int, username: str):
        """Отключает пользователя от чата."""
        if chat_id in self.chat_connections:
            if username in self.chat_connections[chat_id]:
                del self.chat_connections[chat_id][username]
                logger.info(f"Пользователь {username} отключился от чата {chat_id}")
            if not self.chat_connections[chat_id]:
                del self.chat_connections[chat_id]

    async def broadcast_to_chat(self, chat_id: int, message: dict, exclude_username: str = None):
        """Отправляет сообщение всем участникам чата."""
        if chat_id not in self.chat_connections:
            return
        
        disconnected = []
        for username, websocket in self.chat_connections[chat_id].items():
            if exclude_username and username == exclude_username:
                continue
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения пользователю {username} в чате {chat_id}: {e}")
                disconnected.append(username)
        
        # Удаляем отключенных пользователей
        for username in disconnected:
            self.disconnect(chat_id, username)

    async def send_to_user_in_chat(self, chat_id: int, username: str, message: dict):
        """Отправляет сообщение конкретному пользователю в чате."""
        if chat_id not in self.chat_connections:
            return
        
        if username not in self.chat_connections[chat_id]:
            return
        
        websocket = self.chat_connections[chat_id][username]
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {username} в чате {chat_id}: {e}")
            self.disconnect(chat_id, username)


chat_manager = AnonymousChatConnectionManager()


@router.post("/start/{username}", response_model=MatchmakingStatusResponse)
async def start_matchmaking(
    username: str,
    session: AsyncSession = Depends(get_db),
) -> MatchmakingStatusResponse:
    """
    Начинает поиск матча для пользователя.
    """
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    # Проверяем, что мессенджеры доступны
    if not user.messengers_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Мессенджеры недоступны. Пройдите опрос.",
        )

    # Проверяем, что профиль завершен
    if not await has_completed_profile(session, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Психологический профиль не завершен. Пройдите опрос.",
        )

    # Добавляем в очередь
    await join_matchmaking_queue(session, user.id)

    # Получаем количество людей в очереди
    queue_count = await get_matchmaking_queue_count(session, exclude_user_id=user.id)

    return MatchmakingStatusResponse(
        is_searching=True,
        queue_count=queue_count,
    )


@router.post("/stop/{username}")
async def stop_matchmaking(
    username: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Останавливает поиск матча для пользователя.
    """
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    await leave_matchmaking_queue(session, user.id)

    return {"message": "Поиск остановлен"}


@router.get("/status/{username}", response_model=MatchmakingStatusResponse)
async def get_matchmaking_status(
    username: str,
    session: AsyncSession = Depends(get_db),
) -> MatchmakingStatusResponse:
    """
    Получает статус матчинга для пользователя.
    """
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    from src.db.models import MatchmakingQueue
    from sqlalchemy import select

    stmt = select(MatchmakingQueue).where(MatchmakingQueue.user_id == user.id)
    result = await session.execute(stmt)
    queue_entry = result.scalar_one_or_none()

    is_searching = queue_entry is not None and queue_entry.is_searching
    queue_count = await get_matchmaking_queue_count(session, exclude_user_id=user.id)

    return MatchmakingStatusResponse(
        is_searching=is_searching,
        queue_count=queue_count,
    )


@router.websocket("/ws/{username}")
async def matchmaking_websocket(websocket: WebSocket, username: str):
    """
    WebSocket эндпоинт для отслеживания статуса матчинга.
    """
    logger.info(f"WebSocket подключение для пользователя {username}")
    
    try:
        await matchmaking_manager.connect(websocket, username)
        logger.info(f"WebSocket подключен для {username}")
    except Exception as e:
        logger.error(f"Ошибка подключения WebSocket для {username}: {e}", exc_info=True)
        return

    search_task = None
    user = None

    try:
        async with AsyncSessionLocal() as session:
            user = await get_user_by_username(session, username)
            if not user:
                logger.warning(f"Пользователь {username} не найден")
                await websocket.send_json({
                    "type": "error",
                    "message": "Пользователь не найден"
                })
                matchmaking_manager.disconnect(username)
                return

            # Проверяем, что мессенджеры доступны
            if not user.messengers_enabled:
                await websocket.send_json({
                    "type": "error",
                    "message": "Мессенджеры недоступны. Пройдите опрос."
                })
                matchmaking_manager.disconnect(username)
                return

            # Проверяем, что профиль завершен
            if not await has_completed_profile(session, user.id):
                await websocket.send_json({
                    "type": "error",
                    "message": "Психологический профиль не завершен. Пройдите опрос."
                })
                matchmaking_manager.disconnect(username)
                return

            # Проверяем статус
            queue_count = await get_matchmaking_queue_count(session, exclude_user_id=user.id)
            await websocket.send_json({
                "type": "status",
                "queue_count": queue_count,
            })

            # Запускаем поиск, если пользователь еще не в очереди
            from src.db.models import MatchmakingQueue, User
            from sqlalchemy import select

            stmt = select(MatchmakingQueue).where(MatchmakingQueue.user_id == user.id)
            result = await session.execute(stmt)
            queue_entry = result.scalar_one_or_none()

            if not queue_entry or not queue_entry.is_searching:
                # Добавляем в очередь
                await join_matchmaking_queue(session, user.id)
                
                # Проверяем, что пользователь действительно в очереди
                verify_stmt = select(MatchmakingQueue).where(MatchmakingQueue.user_id == user.id)
                verify_result = await session.execute(verify_stmt)
                verify_entry = verify_result.scalar_one_or_none()
                logger.info(f"✓ Пользователь {username} (id={user.id}) добавлен в очередь: {verify_entry is not None and verify_entry.is_searching}")
                
                queue_count = await get_matchmaking_queue_count(session, exclude_user_id=user.id)
                logger.info(f"✓ Других пользователей в очереди на момент подключения {username}: {queue_count}")
                
                await websocket.send_json({
                    "type": "searching_started",
                    "queue_count": queue_count,
                })
                logger.info(f"Пользователь {username} добавлен в очередь матчинга")

            # Запускаем фоновый поиск
            async def search_loop():
                try:
                    logger.info(f"Начало поиска матча для {username}")
                    first_check = True
                    while True:
                        # Первая проверка сразу, остальные через 2 секунды
                        if first_check:
                            first_check = False
                            await asyncio.sleep(0.5)  # Небольшая задержка для синхронизации БД
                        else:
                            await asyncio.sleep(2)  # Проверяем каждые 2 секунды для быстрого мэтчинга

                        async with AsyncSessionLocal() as search_session:
                            # Обновляем счетчик
                            current_count = await get_matchmaking_queue_count(
                                search_session,
                                exclude_user_id=user.id,
                            )
                            logger.info(f"[{username}] Пользователей в очереди: {current_count}")
                            try:
                                await websocket.send_json({
                                    "type": "queue_update",
                                    "queue_count": current_count,
                                })
                            except Exception as send_error:
                                logger.error(f"Ошибка отправки обновления очереди для {username}: {send_error}")
                                break

                            # Пытаемся найти матч
                            try:
                                logger.info(f"[{username}] Попытка найти матч...")
                                chat = await find_match(search_session, user.id)
                                if chat:
                                    logger.info(f"Матч найден для {username}: чат {chat.id}")
                                    
                                    # Определяем второго пользователя
                                    other_user_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
                                    other_user_stmt = select(User).where(User.id == other_user_id)
                                    other_user_result = await search_session.execute(other_user_stmt)
                                    other_user = other_user_result.scalar_one_or_none()
                                    
                                    # Отправляем уведомление текущему пользователю
                                    await websocket.send_json({
                                        "type": "match_found",
                                        "chat_id": chat.id,
                                    })
                                    
                                    # Отправляем уведомление второму пользователю через matchmaking_manager
                                    if other_user:
                                        logger.info(f"Отправка уведомления второму пользователю {other_user.username}")
                                        await matchmaking_manager.send_personal_message(
                                            {
                                                "type": "match_found",
                                                "chat_id": chat.id,
                                            },
                                            other_user.username
                                        )
                                    
                                    # Небольшая задержка, чтобы убедиться, что сообщения доставлены
                                    await asyncio.sleep(0.1)
                                    
                                    matchmaking_manager.disconnect(username)
                                    break
                            except Exception as match_error:
                                logger.error(f"Ошибка при поиске матча для {username}: {match_error}", exc_info=True)
                except asyncio.CancelledError:
                    logger.info(f"Поиск матча отменен для {username}")
                except Exception as e:
                    logger.error(f"Ошибка в поиске матча для {username}: {e}", exc_info=True)
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Ошибка поиска: {str(e)}",
                        })
                    except:
                        pass

            # Запускаем поиск в фоне
            search_task = asyncio.create_task(search_loop())
            matchmaking_manager.searching_users[username] = search_task

            # Обрабатываем сообщения от клиента
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    logger.info(f"Получено сообщение от {username}: {message}")

                    if message.get("type") == "stop_search":
                        logger.info(f"Остановка поиска для {username}")
                        async with AsyncSessionLocal() as stop_session:
                            await leave_matchmaking_queue(stop_session, user.id)
                        if search_task:
                            search_task.cancel()
                        await websocket.send_json({
                            "type": "search_stopped",
                        })
                        break

                except WebSocketDisconnect:
                    logger.info(f"WebSocket отключен для пользователя {username}")
                    break
                except json.JSONDecodeError as e:
                    logger.error(f"Ошибка парсинга JSON от {username}: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Неверный формат сообщения",
                    })

    except WebSocketDisconnect:
        logger.info(f"WebSocket отключен для пользователя {username}")
    except Exception as e:
        logger.error(f"Ошибка в WebSocket для {username}: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Произошла внутренняя ошибка сервера.",
            })
        except:
            pass
    finally:
        # Отменяем задачу поиска
        if search_task:
            search_task.cancel()
        
        matchmaking_manager.disconnect(username)
        
        # Удаляем из очереди при отключении
        if user:
            try:
                async with AsyncSessionLocal() as cleanup_session:
                    await leave_matchmaking_queue(cleanup_session, user.id)
                    logger.info(f"Пользователь {username} удален из очереди матчинга")
            except Exception as e:
                logger.error(f"Ошибка при очистке очереди для {username}: {e}")


@router.websocket("/chat/{chat_id}/ws/{username}")
async def anonymous_chat_websocket(websocket: WebSocket, chat_id: int, username: str):
    """
    WebSocket эндпоинт для обмена сообщениями в анонимном чате в реальном времени.
    """
    logger.info(f"WebSocket подключение к чату {chat_id} от пользователя {username}")
    
    user = None
    
    try:
        async with AsyncSessionLocal() as session:
            # Проверяем пользователя
            user = await get_user_by_username(session, username)
            if not user:
                logger.warning(f"Пользователь {username} не найден")
                await websocket.close(code=4004, reason="Пользователь не найден")
                return

            # Проверяем доступ к чату
            chat = await get_anonymous_chat(session, chat_id, user.id)
            if not chat:
                logger.warning(f"Чат {chat_id} не найден для пользователя {username}")
                await websocket.close(code=4004, reason="Чат не найден")
                return

        # Подключаем к чату
        await chat_manager.connect(websocket, chat_id, username)

        # Отправляем подтверждение подключения
        await websocket.send_json({
            "type": "connected",
            "chat_id": chat_id,
        })

        # Слушаем сообщения (в данном случае просто поддерживаем соединение)
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Обрабатываем ping для поддержания соединения
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket отключен для пользователя {username} в чате {chat_id}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON от {username}: {e}")
            except Exception as e:
                logger.error(f"Ошибка в WebSocket для {username} в чате {chat_id}: {e}", exc_info=True)
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket отключен для пользователя {username} в чате {chat_id}")
    except Exception as e:
        logger.error(f"Ошибка в WebSocket для {username} в чате {chat_id}: {e}", exc_info=True)
    finally:
        chat_manager.disconnect(chat_id, username)


@router.get("/chats/{username}")
async def get_anonymous_chats(
    username: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Получает список анонимных чатов пользователя.
    """
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    chats = await get_user_anonymous_chats(session, user.id)

    # Формируем ответ
    result = []
    for chat in chats:
        # Определяем собеседника
        other_user = chat.user2 if chat.user1_id == user.id else chat.user1

        # Получаем последнее сообщение
        last_message = None
        last_message_time = None
        unread_count = 0
        if chat.messages:
            last_msg = chat.messages[-1]
            last_message = last_msg.content[:50]  # Первые 50 символов
            last_message_time = last_msg.created_at.isoformat()
            # Считаем непрочитанные (сообщения не от пользователя)
            unread_count = sum(1 for msg in chat.messages if msg.sender_id != user.id and not msg.is_read)

        result.append({
            "id": chat.id,
            "user1_id": chat.user1_id,
            "user2_id": chat.user2_id,
            "created_at": chat.created_at.isoformat(),
            "updated_at": chat.updated_at.isoformat(),
            "last_message": last_message,
            "last_message_time": last_message_time,
            "unread_count": unread_count,
            "user1_revealed": chat.user1_revealed,
            "user2_revealed": chat.user2_revealed,
            "other_user_revealed": chat.user2_revealed if chat.user1_id == user.id else chat.user1_revealed,
        })

    return result


@router.get("/public-chats/{username}")
async def get_public_chats(
    username: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Получает список раскрытых (публичных) чатов пользователя.
    """
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    chats = await get_user_public_chats(session, user.id)

    result = []
    for chat in chats:
        other_user = chat.user2 if chat.user1_id == user.id else chat.user1

        last_message = None
        last_message_time = None
        unread_count = 0
        if chat.messages:
            last_msg = chat.messages[-1]
            last_message = last_msg.content[:50]
            last_message_time = last_msg.created_at.isoformat()
            unread_count = sum(1 for msg in chat.messages if msg.sender_id != user.id and not msg.is_read)

        result.append({
            "id": chat.id,
            "other_user_id": other_user.id,
            "name": other_user.username,
            "avatar": other_user.avatar or "",
            "created_at": chat.created_at.isoformat(),
            "updated_at": chat.updated_at.isoformat(),
            "last_message": last_message,
            "last_message_time": last_message_time,
            "unread_count": unread_count,
        })

    return result


@router.get("/chat/{chat_id}/{username}")
async def get_anonymous_chat_messages(
    chat_id: int,
    username: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Получает сообщения анонимного чата.
    """
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    chat = await get_anonymous_chat(session, chat_id, user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден",
        )

    # Формируем сообщения
    messages = []
    for msg in chat.messages:
        messages.append({
            "id": msg.id,
            "content": msg.content,
            "sender_id": msg.sender_id,
            "is_mine": msg.sender_id == user.id,
            "created_at": msg.created_at.isoformat(),
        })

    # Определяем собеседника
    other_user = chat.user2 if chat.user1_id == user.id else chat.user1

    return {
        "chat_id": chat.id,
        "other_user_id": other_user.id,
        "messages": messages,
    }


@router.post("/chat/{chat_id}/message/{username}")
async def send_anonymous_message(
    chat_id: int,
    username: str,
    request: SendAnonymousMessageRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Отправляет сообщение в анонимный чат.
    """
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    try:
        message = await create_anonymous_message(
            session,
            chat_id,
            user.id,
            request.text,
        )

        # Отправляем сообщение через WebSocket другому участнику
        await chat_manager.broadcast_to_chat(
            chat_id,
            {
                "type": "new_message",
                "message": {
                    "id": message.id,
                    "content": message.content,
                    "sender_id": message.sender_id,
                    "is_mine": False,  # Для получателя это не его сообщение
                    "created_at": message.created_at.isoformat(),
                }
            },
            exclude_username=username  # Не отправляем отправителю
        )

        return {
            "id": message.id,
            "content": message.content,
            "sender_id": message.sender_id,
            "is_mine": True,
            "created_at": message.created_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/chat/{chat_id}/reveal/{username}")
async def reveal_chat(
    chat_id: int,
    username: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Отмечает желание пользователя раскрыться в анонимном чате.
    Если оба пользователя согласны, переводит чат в публичный и уведомляет обоих через WebSocket.
    """
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    try:
        chat, both_revealed = await reveal_anonymous_chat(session, chat_id, user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    other_user = chat.user2 if chat.user1_id == user.id else chat.user1

    # Отправляем уведомление через WebSocket другому пользователю
    if both_revealed:
        # Оба согласны - уведомляем обоих, что чат стал публичным
        last_message = None
        last_message_time = None
        if chat.messages:
            last_msg = chat.messages[-1]
            last_message = last_msg.content[:50]
            last_message_time = last_msg.created_at.isoformat()

        # Формируем данные для обоих пользователей
        chat_data_for_user = {
            "type": "chat_revealed",
            "chat_id": chat.id,
            "is_public": True,
            "both_revealed": True,
            "other_user": {
                "id": other_user.id,
                "username": other_user.username,
                "avatar": other_user.avatar or "",
            },
            "last_message": last_message,
            "last_message_time": last_message_time,
        }

        chat_data_for_other = {
            "type": "chat_revealed",
            "chat_id": chat.id,
            "is_public": True,
            "both_revealed": True,
            "other_user": {
                "id": user.id,
                "username": user.username,
                "avatar": user.avatar or "",
            },
            "last_message": last_message,
            "last_message_time": last_message_time,
        }

        # Отправляем уведомления через WebSocket
        await chat_manager.send_to_user_in_chat(chat_id, username, chat_data_for_user)
        await chat_manager.send_to_user_in_chat(chat_id, other_user.username, chat_data_for_other)

        return {
            "status": "revealed",
            "message": "Оба пользователя согласны раскрыться. Чат переведен в публичный.",
            "is_public": True,
            "both_revealed": True,
            "chat": {
                "id": chat.id,
                "name": other_user.username,
                "avatar": other_user.avatar or "",
                "last_message": last_message,
                "last_message_time": last_message_time,
            }
        }
    else:
        # Только один пользователь согласился - уведомляем другого
        await chat_manager.send_to_user_in_chat(
            chat_id,
            other_user.username,
            {
                "type": "reveal_request",
                "chat_id": chat.id,
                "message": "Собеседник хочет раскрыться",
            }
        )

        return {
            "status": "pending",
            "message": "Ваше желание раскрыться отправлено собеседнику. Ожидаем его согласия.",
            "is_public": False,
            "both_revealed": False,
            "user1_revealed": chat.user1_revealed,
            "user2_revealed": chat.user2_revealed,
        }

