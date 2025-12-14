from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
    Request,
)
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict
import json
import logging
import asyncio
from src.db.session import get_db, AsyncSessionLocal
from src.db.crud.auth import get_user_by_email, get_user_by_nickname


async def verify_user_active_for_matchmaking(email: str, session: AsyncSession) -> None:
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
    summarize_message_text,
    mark_messages_as_read,
)
from src.db.crud.psychological import has_completed_profile
from src.db.models import User
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/matchmaking", tags=["matchmaking"])


class MatchmakingStatusResponse(BaseModel):
    is_searching: bool
    queue_count: int
    chat_id: int | None = None


class AnonymousChatSchema(BaseModel):
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
    id: int
    content: str
    sender_id: int
    is_mine: bool
    created_at: str

    class Config:
        from_attributes = True


class SendAnonymousMessageRequest(BaseModel):
    text: str


def build_message_payload(
    message, *, current_user_id: int | None = None, is_mine_override: bool | None = None
):
    payload = {
        "id": message.id,
        "content": message.content,
        "sender_id": message.sender_id,
        "created_at": message.created_at.isoformat(),
    }
    if is_mine_override is not None:
        payload["is_mine"] = is_mine_override
    elif current_user_id is not None:
        payload["is_mine"] = message.sender_id == current_user_id
    else:
        payload["is_mine"] = False
    return payload


class MatchmakingConnectionManager:

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.searching_users: Dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        if username in self.active_connections:
            old_ws = self.active_connections[username]
            try:
                if old_ws.client_state.name != "DISCONNECTED":
                    await old_ws.close(code=1001, reason="New connection")
            except:
                pass
        self.active_connections[username] = websocket
        logger.info(
            f"Пользователь {username} подключен к WebSocket matchmaking. Всего активных соединений: {len(self.active_connections)}"
        )

    def disconnect(self, username: str):
        if username in self.active_connections:
            del self.active_connections[username]
        if username in self.searching_users:
            self.searching_users[username].cancel()
            del self.searching_users[username]

    async def send_personal_message(self, message: dict, username: str):
        if username in self.active_connections:
            websocket = self.active_connections[username]
            try:
                await websocket.send_json(message)
                logger.info(
                    f"Сообщение отправлено пользователю {username} через WebSocket"
                )
            except Exception as e:
                logger.error(
                    f"Ошибка отправки сообщения через WebSocket для пользователя {username}: {e}"
                )
                self.disconnect(username)
        else:
            logger.warning(
                f"Пользователь {username} не подключен к WebSocket matchmaking. Активные соединения: {list(self.active_connections.keys())}"
            )

    async def send_notification(self, username: str, notification_data: dict):
        logger.info(
            f"Попытка отправить уведомление пользователю {username}: {notification_data}"
        )
        notification_message = {"type": "notification", **notification_data}
        await self.send_personal_message(notification_message, username)


matchmaking_manager = MatchmakingConnectionManager()


class AnonymousChatConnectionManager:

    def __init__(self):
        self.chat_connections: Dict[int, Dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, chat_id: int, username: str):
        await websocket.accept()
        if chat_id not in self.chat_connections:
            self.chat_connections[chat_id] = {}
        self.chat_connections[chat_id][username] = websocket
        logger.info(f"Пользователь {username} подключился к чату {chat_id}")

    def disconnect(self, chat_id: int, username: str):
        if chat_id in self.chat_connections:
            if username in self.chat_connections[chat_id]:
                del self.chat_connections[chat_id][username]
                logger.info(f"Пользователь {username} отключился от чата {chat_id}")
            if not self.chat_connections[chat_id]:
                del self.chat_connections[chat_id]

    async def broadcast_to_chat(
        self, chat_id: int, message: dict, exclude_username: str = None
    ):
        if chat_id not in self.chat_connections:
            logger.warning(
                f"broadcast_to_chat: Чат {chat_id} не найден в активных соединениях"
            )
            return
        connected_users = list(self.chat_connections[chat_id].keys())
        logger.info(
            f"broadcast_to_chat: Отправка сообщения в чат {chat_id}. Подключенные пользователи: {connected_users}, исключаем: {exclude_username}"
        )
        disconnected = []
        sent_count = 0
        for username, websocket in self.chat_connections[chat_id].items():
            if exclude_username and username == exclude_username:
                logger.debug(f"broadcast_to_chat: Пропускаем отправителя {username}")
                continue
            try:
                await websocket.send_json(message)
                sent_count += 1
                logger.info(
                    f"broadcast_to_chat: Сообщение успешно отправлено пользователю {username} в чате {chat_id}"
                )
            except Exception as e:
                logger.error(
                    f"Ошибка отправки сообщения пользователю {username} в чате {chat_id}: {e}"
                )
                disconnected.append(username)
        logger.info(
            f"broadcast_to_chat: Сообщение отправлено {sent_count} пользователям в чате {chat_id}"
        )
        for username in disconnected:
            self.disconnect(chat_id, username)

    async def send_to_user_in_chat(self, chat_id: int, username: str, message: dict):
        if chat_id not in self.chat_connections:
            return
        if username not in self.chat_connections[chat_id]:
            return
        websocket = self.chat_connections[chat_id][username]
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(
                f"Ошибка отправки сообщения пользователю {username} в чате {chat_id}: {e}"
            )
            self.disconnect(chat_id, username)

    def is_user_connected_to_chat(self, chat_id: int, username: str) -> bool:
        if chat_id not in self.chat_connections:
            logger.debug(
                f"is_user_connected_to_chat: Чат {chat_id} не найден в активных соединениях"
            )
            return False
        if username not in self.chat_connections[chat_id]:
            logger.debug(
                f"is_user_connected_to_chat: Пользователь {username} не найден в чате {chat_id}. Активные пользователи: {list(self.chat_connections[chat_id].keys())}"
            )
            return False
        websocket = self.chat_connections[chat_id][username]
        try:
            is_active = websocket.client_state.name not in ("DISCONNECTED", "CLOSED")
            logger.debug(
                f"is_user_connected_to_chat: Пользователь {username} в чате {chat_id}, состояние соединения: {websocket.client_state.name}, is_active={is_active}"
            )
            return is_active
        except Exception as e:
            logger.warning(
                f"is_user_connected_to_chat: Ошибка при проверке состояния соединения для {username} в чате {chat_id}: {e}"
            )
            return False


chat_manager = AnonymousChatConnectionManager()


@router.post("/start/{email}", response_model=MatchmakingStatusResponse)
async def start_matchmaking(
    request: Request, email: str, session: AsyncSession = Depends(get_db)
) -> MatchmakingStatusResponse:
    await verify_user_active_for_matchmaking(email, session)
    user = await get_user_by_email(session, email)
    if not user.messengers_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Мессенджеры недоступны. Пройдите опрос.",
        )
    if not await has_completed_profile(session, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Психологический профиль не завершен. Пройдите опрос.",
        )
    await join_matchmaking_queue(session, user.id)
    chat_found = None
    try:
        chat_found = await find_match(session, user.id, threshold=0.95)
    except Exception as match_error:
        logger.error(
            f"Ошибка мгновенного матчинга для {email}: {match_error}", exc_info=True
        )
    queue_count = await get_matchmaking_queue_count(session, exclude_user_id=user.id)
    if chat_found:
        logger.info(f"Мгновенный матч найден в REST для {email}: чат {chat_found.id}")
        other_user_id = (
            chat_found.user2_id
            if chat_found.user1_id == user.id
            else chat_found.user1_id
        )
        other_user_stmt = select(User).where(User.id == other_user_id)
        other_user_result = await session.execute(other_user_stmt)
        other_user = other_user_result.scalar_one_or_none()
        payload = {"type": "match_found", "chat_id": chat_found.id}
        await matchmaking_manager.send_personal_message(payload, email)
        if other_user:
            await matchmaking_manager.send_personal_message(payload, other_user.email)
        return MatchmakingStatusResponse(
            is_searching=False, queue_count=queue_count, chat_id=chat_found.id
        )
    return MatchmakingStatusResponse(is_searching=True, queue_count=queue_count)


@router.post("/stop/{email}")
async def stop_matchmaking(email: str, session: AsyncSession = Depends(get_db)):
    await verify_user_active_for_matchmaking(email, session)
    user = await get_user_by_email(session, email)
    await leave_matchmaking_queue(session, user.id)
    return {"message": "Поиск остановлен"}


@router.get("/status/{email}", response_model=MatchmakingStatusResponse)
async def get_matchmaking_status(
    email: str, session: AsyncSession = Depends(get_db)
) -> MatchmakingStatusResponse:
    await verify_user_active_for_matchmaking(email, session)
    user = await get_user_by_email(session, email)
    from src.db.models import MatchmakingQueue
    from sqlalchemy import select

    stmt = select(MatchmakingQueue).where(MatchmakingQueue.user_id == user.id)
    result = await session.execute(stmt)
    queue_entry = result.scalar_one_or_none()
    is_searching = queue_entry is not None and queue_entry.is_searching
    queue_count = await get_matchmaking_queue_count(session, exclude_user_id=user.id)
    return MatchmakingStatusResponse(is_searching=is_searching, queue_count=queue_count)


@router.websocket("/ws/{email}")
async def matchmaking_websocket(websocket: WebSocket, email: str):
    logger.info(f"WebSocket подключение для пользователя {email}")
    try:
        await matchmaking_manager.connect(websocket, email)
        logger.info(f"WebSocket подключен для {email}")
        await websocket.send_json(
            {"type": "connected", "message": "WebSocket подключен"}
        )
    except Exception as e:
        logger.error(f"Ошибка подключения WebSocket для {email}: {e}", exc_info=True)
        return
    search_task = None
    user = None
    ping_task = None
    try:

        async def initialize_user():
            nonlocal user
            async with AsyncSessionLocal() as session:
                user = await get_user_by_email(session, email)
                if not user:
                    logger.warning(f"Пользователь {email} не найден")
                    await websocket.send_json(
                        {"type": "error", "message": "Пользователь не найден"}
                    )
                    matchmaking_manager.disconnect(email)
                    return False
                if user.is_banned:
                    logger.warning(
                        f"Пользователь {email} забанен, отключение WebSocket"
                    )
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Ваш аккаунт заблокирован администратором. Доступ запрещен.",
                        }
                    )
                    matchmaking_manager.disconnect(email)
                    await websocket.close(code=4003, reason="Аккаунт заблокирован")
                    return False
                if not user.messengers_enabled:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Мессенджеры недоступны. Пройдите опрос.",
                        }
                    )
                    matchmaking_manager.disconnect(email)
                    return False
                if not await has_completed_profile(session, user.id):
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Психологический профиль не завершен. Пройдите опрос.",
                        }
                    )
                    matchmaking_manager.disconnect(email)
                    return False
                queue_count = await get_matchmaking_queue_count(
                    session, exclude_user_id=user.id
                )
                from src.db.models import MatchmakingQueue, User
                from sqlalchemy import select

                stmt = select(MatchmakingQueue).where(
                    MatchmakingQueue.user_id == user.id
                )
                result = await session.execute(stmt)
                queue_entry = result.scalar_one_or_none()
                is_searching = queue_entry is not None and queue_entry.is_searching
                await websocket.send_json(
                    {
                        "type": "status",
                        "is_searching": is_searching,
                        "queue_count": queue_count,
                    }
                )
                return is_searching

        is_searching = await initialize_user()
        if is_searching is False:
            return

        async def ping_loop():
            try:
                while True:
                    await asyncio.sleep(30)
                    try:
                        await websocket.send_json({"type": "ping"})
                    except Exception as e:
                        logger.error(f"Ошибка отправки ping для {email}: {e}")
                        break
            except asyncio.CancelledError:
                pass

        ping_task = asyncio.create_task(ping_loop())
        if is_searching:

            async def search_loop():
                try:
                    logger.info(f"Начало поиска матча для {email}")
                    wait_duration = 20
                    wait_interval = 3
                    elapsed = 0
                    logger.info(
                        f"[{email}] Ожидание накопления очереди ({wait_duration} секунд)..."
                    )
                    try:
                        await websocket.send_json(
                            {
                                "type": "waiting_for_queue",
                                "message": f"Ожидание накопления очереди... ({wait_duration} сек)",
                                "remaining_seconds": wait_duration,
                            }
                        )
                    except Exception as send_error:
                        logger.warning(
                            f"Не удалось отправить сообщение о ожидании для {email}: {send_error}"
                        )
                    while elapsed < wait_duration:
                        await asyncio.sleep(wait_interval)
                        elapsed += wait_interval
                        remaining = wait_duration - elapsed
                        async with AsyncSessionLocal() as wait_session:
                            current_count = await get_matchmaking_queue_count(
                                wait_session, exclude_user_id=user.id
                            )
                        logger.info(
                            f"[{email}] Ожидание... В очереди: {current_count}, осталось: {remaining} сек"
                        )
                        try:
                            await websocket.send_json(
                                {
                                    "type": "queue_update",
                                    "queue_count": current_count,
                                    "status": "waiting",
                                    "remaining_seconds": remaining,
                                }
                            )
                        except Exception as send_error:
                            logger.warning(
                                f"Ошибка отправки обновления очереди для {email}: {send_error}"
                            )
                    logger.info(f"[{email}] Период ожидания завершен, начинаем поиск")
                    try:
                        await websocket.send_json(
                            {
                                "type": "searching",
                                "message": "Поиск самого похожего собеседника...",
                            }
                        )
                    except Exception as send_error:
                        logger.warning(
                            f"Не удалось отправить сообщение о начале поиска для {email}: {send_error}"
                        )
                    current_threshold = 0.9
                    first_attempt = True
                    min_threshold = 0.6
                    search_interval = 3
                    while True:
                        if not first_attempt:
                            await asyncio.sleep(search_interval)
                            if current_threshold > 0.8:
                                current_threshold -= 0.03
                            elif current_threshold > 0.7:
                                current_threshold -= 0.02
                            else:
                                current_threshold -= 0.01
                            if current_threshold < min_threshold:
                                current_threshold = min_threshold
                                logger.info(
                                    f"[{email}] Порог достиг минимума {min_threshold}"
                                )
                        else:
                            first_attempt = False
                        async with AsyncSessionLocal() as search_session:
                            current_count = await get_matchmaking_queue_count(
                                search_session, exclude_user_id=user.id
                            )
                        logger.info(
                            f"[{email}] Пользователей в очереди: {current_count}, порог: {current_threshold:.3f}"
                        )
                        try:
                            await websocket.send_json(
                                {
                                    "type": "queue_update",
                                    "queue_count": current_count,
                                    "status": "searching",
                                    "threshold": current_threshold,
                                }
                            )
                        except Exception as send_error:
                            logger.error(
                                f"Ошибка отправки обновления очереди для {email}: {send_error}"
                            )
                            break
                        try:
                            logger.info(
                                f"[{email}] Попытка найти матч с порогом {current_threshold:.3f}..."
                            )
                            async with AsyncSessionLocal() as search_session:
                                chat = await find_match(
                                    search_session, user.id, threshold=current_threshold
                                )
                                if chat:
                                    logger.info(
                                        f"✓ Матч найден для {email}: чат {chat.id} (порог: {current_threshold:.3f})"
                                    )
                                    other_user_id = (
                                        chat.user2_id
                                        if chat.user1_id == user.id
                                        else chat.user1_id
                                    )
                                    other_user_stmt = select(User).where(
                                        User.id == other_user_id
                                    )
                                    other_user_result = await search_session.execute(
                                        other_user_stmt
                                    )
                                    other_user = other_user_result.scalar_one_or_none()
                                    await websocket.send_json(
                                        {"type": "match_found", "chat_id": chat.id}
                                    )
                                    if other_user:
                                        logger.info(
                                            f"Отправка уведомления второму пользователю {other_user.email}"
                                        )
                                        await matchmaking_manager.send_personal_message(
                                            {"type": "match_found", "chat_id": chat.id},
                                            other_user.email,
                                        )
                                    await asyncio.sleep(0.1)
                                    matchmaking_manager.disconnect(email)
                                    break
                        except Exception as match_error:
                            logger.error(
                                f"Ошибка при поиске матча для {email}: {match_error}",
                                exc_info=True,
                            )
                except asyncio.CancelledError:
                    logger.info(f"Поиск матча отменен для {email}")
                except Exception as e:
                    logger.error(
                        f"Ошибка в поиске матча для {email}: {e}", exc_info=True
                    )
                    try:
                        await websocket.send_json(
                            {"type": "error", "message": f"Ошибка поиска: {str(e)}"}
                        )
                    except:
                        pass
                search_task = asyncio.create_task(search_loop())

            matchmaking_manager.searching_users[email] = search_task
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    logger.info(f"Получено сообщение от {email}: {message}")
                    if message.get("type") == "pong":
                        continue
                    elif message.get("type") == "stop_search":
                        logger.info(f"Остановка поиска для {email}")
                        async with AsyncSessionLocal() as stop_session:
                            await leave_matchmaking_queue(stop_session, user.id)
                        if search_task:
                            search_task.cancel()
                        await websocket.send_json({"type": "search_stopped"})
                        break
                except WebSocketDisconnect:
                    logger.info(f"WebSocket отключен для пользователя {email}")
                    break
                except json.JSONDecodeError as e:
                    logger.error(f"Ошибка парсинга JSON от {email}: {e}")
                    await websocket.send_json(
                        {"type": "error", "message": "Неверный формат сообщения"}
                    )
    except WebSocketDisconnect:
        logger.info(f"WebSocket отключен для пользователя {username}")
    except Exception as e:
        logger.error(f"Ошибка в WebSocket для {email}: {e}", exc_info=True)
        try:
            await websocket.send_json(
                {"type": "error", "message": "Произошла внутренняя ошибка сервера."}
            )
        except Exception:
            logger.warning(
                f"Не удалось отправить сообщение об ошибке пользователю {email}"
            )
    finally:
        try:
            if ping_task and (not ping_task.done()):
                ping_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    pass
        except Exception as e:
            logger.error(f"Ошибка при отмене задачи ping для {email}: {e}")
        try:
            if search_task and (not search_task.done()):
                search_task.cancel()
                try:
                    await search_task
                except asyncio.CancelledError:
                    pass
        except Exception as e:
            logger.error(f"Ошибка при отмене задачи поиска для {email}: {e}")
        try:
            matchmaking_manager.disconnect(email)
        except Exception as e:
            logger.error(
                f"Ошибка при отключении пользователя {email} из менеджера: {e}"
            )
        if user:
            try:
                async with AsyncSessionLocal() as cleanup_session:
                    await leave_matchmaking_queue(cleanup_session, user.id)
                    logger.info(f"Пользователь {email} удален из очереди матчинга")
            except Exception as e:
                logger.error(f"Ошибка при очистке очереди для {username}: {e}")
        try:
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.close(code=1000)
        except Exception as e:
            logger.warning(f"Ошибка при закрытии WebSocket для {email}: {e}")


@router.websocket("/chat/{chat_id}/ws/{username}")
async def anonymous_chat_websocket(websocket: WebSocket, chat_id: int, username: str):
    email = username
    logger.info(f"WebSocket подключение к чату {chat_id} от пользователя {email}")
    user = None
    try:
        async with AsyncSessionLocal() as session:
            user = await get_user_by_email(session, email)
            if not user:
                logger.warning(f"Пользователь {email} не найден")
                await websocket.close(code=4004, reason="Пользователь не найден")
                return
            if user.is_banned:
                logger.warning(
                    f"Пользователь {email} забанен, отключение WebSocket чата"
                )
                await websocket.close(
                    code=4003, reason="Аккаунт заблокирован администратором"
                )
                return
            chat = await get_anonymous_chat(session, chat_id, user.id)
            if not chat:
                logger.warning(f"Чат {chat_id} не найден для пользователя {email}")
                await websocket.close(code=4004, reason="Чат не найден")
                return
            await chat_manager.connect(websocket, chat_id, email)
            logger.info(
                f"Пользователь {email} успешно подключен к WebSocket чата {chat_id}. Активные соединения в чате: {list(chat_manager.chat_connections.get(chat_id, {}).keys())}"
            )
        try:
            async with AsyncSessionLocal() as read_session:
                await mark_messages_as_read(read_session, chat_id, user.id)
                logger.info(
                    f"Сообщения помечены как прочитанные для {email} в чате {chat_id} при подключении"
                )
        except Exception as e:
            logger.error(
                f"Ошибка при пометке сообщений как прочитанных для {email} в чате {chat_id}: {e}"
            )
        await websocket.send_json({"type": "connected", "chat_id": chat_id})
        logger.info(
            f"Отправлено подтверждение подключения пользователю {email} в чате {chat_id}"
        )
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                logger.info(
                    f"WebSocket отключен для пользователя {username} в чате {chat_id}"
                )
                break
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON от {username}: {e}")
            except Exception as e:
                logger.error(
                    f"Ошибка в WebSocket для {email} в чате {chat_id}: {e}",
                    exc_info=True,
                )
                break
    except WebSocketDisconnect:
        logger.info(f"WebSocket отключен для пользователя {username} в чате {chat_id}")
    except Exception as e:
        logger.error(
            f"Ошибка в WebSocket для {username} в чате {chat_id}: {e}", exc_info=True
        )
        try:
            await websocket.send_json(
                {"type": "error", "message": "Произошла ошибка соединения"}
            )
        except Exception:
            pass
    finally:
        try:
            chat_manager.disconnect(chat_id, email)
        except Exception as e:
            logger.error(
                f"Ошибка при отключении пользователя {email} из чата {chat_id}: {e}"
            )
        try:
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.close(code=1000)
        except Exception as e:
            logger.warning(
                f"Ошибка при закрытии WebSocket для {email} в чате {chat_id}: {e}"
            )


@router.get("/chats/{email}")
async def get_anonymous_chats(email: str, session: AsyncSession = Depends(get_db)):
    await verify_user_active_for_matchmaking(email, session)
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )
    chats = await get_user_anonymous_chats(session, user.id)
    result = []
    for chat in chats:
        other_user = chat.user2 if chat.user1_id == user.id else chat.user1
        other_alias = chat.user2_alias if chat.user1_id == user.id else chat.user1_alias
        other_alias = other_alias or "Собеседник"
        last_message = None
        last_message_time = None
        unread_count = 0
        if chat.messages:
            last_msg = None
            for msg in chat.messages:
                if msg.sender_id != user.id and (not msg.is_read):
                    unread_count += 1
                if last_msg is None or msg.created_at > last_msg.created_at:
                    last_msg = msg
            if last_msg:
                last_message = summarize_message_text(last_msg)
                last_message_time = last_msg.created_at.isoformat()
        result.append(
            {
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
                "other_user_revealed": (
                    chat.user2_revealed
                    if chat.user1_id == user.id
                    else chat.user1_revealed
                ),
                "name": other_alias,
            }
        )
    return result


@router.get("/public-chats/{email}")
async def get_public_chats(email: str, session: AsyncSession = Depends(get_db)):
    await verify_user_active_for_matchmaking(email, session)
    user = await get_user_by_email(session, email)
    chats = await get_user_public_chats(session, user.id)
    result = []
    for chat in chats:
        other_user = chat.user2 if chat.user1_id == user.id else chat.user1
        last_message = None
        last_message_time = None
        unread_count = 0
        if chat.messages:
            last_msg = None
            for msg in chat.messages:
                if msg.sender_id != user.id and (not msg.is_read):
                    unread_count += 1
                if last_msg is None or msg.created_at > last_msg.created_at:
                    last_msg = msg
            if last_msg:
                last_message = summarize_message_text(last_msg)
                last_message_time = last_msg.created_at.isoformat()
        result.append(
            {
                "id": chat.id,
                "other_user_id": other_user.id,
                "name": other_user.nickname,
                "created_at": chat.created_at.isoformat(),
                "updated_at": chat.updated_at.isoformat(),
                "last_message": last_message,
                "last_message_time": last_message_time,
                "unread_count": unread_count,
            }
        )
    return result


@router.get("/chat/{chat_id}/{email}")
async def get_anonymous_chat_messages(
    chat_id: int, email: str, session: AsyncSession = Depends(get_db)
):
    await verify_user_active_for_matchmaking(email, session)
    user = await get_user_by_email(session, email)
    chat = await get_anonymous_chat(session, chat_id, user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден"
        )
    messages = [
        build_message_payload(msg, current_user_id=user.id) for msg in chat.messages
    ]
    other_user = chat.user2 if chat.user1_id == user.id else chat.user1
    other_alias = chat.user2_alias if chat.user1_id == user.id else chat.user1_alias
    other_alias = other_alias or "Собеседник"
    return {
        "chat_id": chat.id,
        "other_user_id": other_user.id,
        "messages": messages,
        "name": other_user.nickname if chat.is_public else other_alias,
        "is_blocked": chat.is_blocked,
        "is_other_user_banned": other_user.is_banned,
    }


@router.put("/chat/{chat_id}/read/{email}")
async def mark_chat_messages_as_read(
    chat_id: int, email: str, session: AsyncSession = Depends(get_db)
):
    await verify_user_active_for_matchmaking(email, session)
    user = await get_user_by_email(session, email)
    try:
        count = await mark_messages_as_read(session, chat_id, user.id)
        return {
            "success": True,
            "marked_count": count,
            "message": f"Помечено {count} сообщений как прочитанных",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/chat/{chat_id}/message/{email}")
async def send_anonymous_message(
    chat_id: int,
    email: str,
    request: SendAnonymousMessageRequest,
    session: AsyncSession = Depends(get_db),
):
    await verify_user_active_for_matchmaking(email, session)
    user = await get_user_by_email(session, email)
    chat = await get_anonymous_chat(session, chat_id, user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден"
        )
    if not chat.is_active:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Чат неактивен")
    if chat.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Чат заблокирован из-за жалобы. Отправка сообщений недоступна.",
        )
    try:
        other_user = chat.user2 if chat.user1_id == user.id else chat.user1
        is_user_in_chat = False
        if other_user:
            is_user_in_chat = chat_manager.is_user_connected_to_chat(
                chat_id, other_user.email
            )
            logger.info(
                f"Проверка подключения для {other_user.email} в чате {chat_id}: is_user_in_chat={is_user_in_chat}"
            )
        message = await create_anonymous_message(
            session, chat_id, user.id, request.text
        )
        if is_user_in_chat and other_user:
            try:
                message.is_read = True
                await session.commit()
                await session.refresh(message)
                logger.info(
                    f"Сообщение {message.id} помечено как прочитанное для {other_user.email}, так как он в активном чате"
                )
            except Exception as e:
                logger.error(f"Ошибка при пометке сообщения как прочитанного: {e}")
        logger.info(
            f"Отправка сообщения через WebSocket в чат {chat_id} от {user.email} к {(other_user.email if other_user else 'None')}"
        )
        await chat_manager.broadcast_to_chat(
            chat_id,
            {
                "type": "new_message",
                "message": build_message_payload(message, is_mine_override=False),
            },
            exclude_username=email,
        )
        response_payload = build_message_payload(
            message, current_user_id=user.id, is_mine_override=True
        )
        if not is_user_in_chat and other_user:

            async def process_notifications():
                try:
                    chat_type = "people" if chat.is_public else "anon"
                    should_notify = False
                    if chat_type == "anon" and other_user.notification_anon_chats:
                        should_notify = True
                    elif chat_type == "people" and other_user.notification_open_chats:
                        should_notify = True
                    logger.info(
                        f"Проверка настроек уведомлений для {other_user.email}: chat_type={chat_type}, should_notify={should_notify}"
                    )
                    if should_notify:
                        async with AsyncSessionLocal() as notify_session:
                            try:
                                from sqlalchemy import select, func
                                from src.db.models import AnonymousMessage

                                stmt = select(func.count(AnonymousMessage.id)).where(
                                    AnonymousMessage.chat_id == chat_id,
                                    AnonymousMessage.sender_id != other_user.id,
                                    AnonymousMessage.is_read == False,
                                )
                                result = await notify_session.execute(stmt)
                                unread_count = result.scalar() or 0
                                if chat.is_public:
                                    chat_name = user.nickname
                                else:
                                    chat_name = (
                                        chat.user2_alias
                                        if chat.user1_id == user.id
                                        else chat.user1_alias
                                    )
                                    chat_name = chat_name or "Собеседник"
                                notification_data = {
                                    "chat_id": chat.id,
                                    "chat_name": chat_name,
                                    "chat_type": chat_type,
                                    "unread_count": unread_count,
                                    "last_message": summarize_message_text(message),
                                }
                                await matchmaking_manager.send_notification(
                                    other_user.email, notification_data
                                )
                                logger.info(
                                    f"Уведомление отправлено пользователю {other_user.email} для чата {chat.id} (тип: {chat_type}, непрочитанных: {unread_count})"
                                )
                            except Exception as e:
                                logger.error(f"Ошибка при отправке уведомления: {e}")
                    else:
                        logger.info(
                            f"Уведомление НЕ отправлено для {other_user.email} (настройки отключены)"
                        )
                except Exception as e:
                    logger.error(f"Ошибка в фоновой обработке уведомлений: {e}")

            asyncio.create_task(process_notifications())
        else:
            logger.info(
                f"Уведомление НЕ отправлено для {(other_user.email if other_user else 'None')} (пользователь в активном чате)"
            )
        return response_payload
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/chat/{chat_id}/reveal/{email}")
async def reveal_chat(
    chat_id: int, email: str, session: AsyncSession = Depends(get_db)
):
    await verify_user_active_for_matchmaking(email, session)
    user = await get_user_by_email(session, email)
    try:
        chat, both_revealed = await reveal_anonymous_chat(session, chat_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    other_user = chat.user2 if chat.user1_id == user.id else chat.user1
    reveal_message_text = (
        "Собеседник хочет раскрыться"
        if not both_revealed
        else "Оба пользователя согласны раскрыться. Чат переведен в публичный."
    )
    reveal_message = await create_anonymous_message(
        session, chat_id, user.id, reveal_message_text
    )
    await chat_manager.send_to_user_in_chat(
        chat_id,
        email,
        {
            "type": "new_message",
            "message": build_message_payload(
                reveal_message, current_user_id=user.id, is_mine_override=True
            ),
        },
    )
    await chat_manager.send_to_user_in_chat(
        chat_id,
        other_user.email,
        {
            "type": "new_message",
            "message": build_message_payload(
                reveal_message, current_user_id=other_user.id, is_mine_override=False
            ),
        },
    )
    if both_revealed:
        last_message = None
        last_message_time = None
        if chat.messages:
            last_msg = chat.messages[-1]
            last_message = summarize_message_text(last_msg)
            last_message_time = last_msg.created_at.isoformat()
        chat_data_for_user = {
            "type": "chat_revealed",
            "chat_id": chat.id,
            "is_public": True,
            "both_revealed": True,
            "other_user": {"id": other_user.id, "username": other_user.nickname},
            "last_message": last_message,
            "last_message_time": last_message_time,
        }
        chat_data_for_other = {
            "type": "chat_revealed",
            "chat_id": chat.id,
            "is_public": True,
            "both_revealed": True,
            "other_user": {"id": user.id, "username": user.nickname},
            "last_message": last_message,
            "last_message_time": last_message_time,
        }
        await chat_manager.send_to_user_in_chat(chat_id, email, chat_data_for_user)
        await chat_manager.send_to_user_in_chat(
            chat_id, other_user.email, chat_data_for_other
        )
        return {
            "status": "revealed",
            "message": "Оба пользователя согласны раскрыться. Чат переведен в публичный.",
            "is_public": True,
            "both_revealed": True,
            "chat": {
                "id": chat.id,
                "name": other_user.nickname,
                "last_message": last_message,
                "last_message_time": last_message_time,
            },
        }
    else:
        await chat_manager.send_to_user_in_chat(
            chat_id,
            other_user.email,
            {
                "type": "reveal_request",
                "chat_id": chat.id,
                "message": "Собеседник хочет раскрыться",
            },
        )
        return {
            "status": "pending",
            "message": "Ваше желание раскрыться отправлено собеседнику. Ожидаем его согласия.",
            "is_public": False,
            "both_revealed": False,
            "user1_revealed": chat.user1_revealed,
            "user2_revealed": chat.user2_revealed,
        }
