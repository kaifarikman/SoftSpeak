from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    Form,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Literal
import json
import logging
import asyncio
from pathlib import Path
import uuid

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
    summarize_message_text,
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


STATIC_DIR = Path(__file__).parent.parent.parent / "static"
CHAT_MEDIA_ROOT = STATIC_DIR / "uploads" / "chat_media"
MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100 MB
PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.m4v', '.webm'}

CHAT_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def build_message_payload(message, *, current_user_id: int | None = None, is_mine_override: bool | None = None):
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

    if message.media_type and message.media_url:
        payload["media"] = {
            "type": message.media_type,
            "url": message.media_url,
            "preview_url": message.media_preview_url,
            "size": message.media_size,
            "duration": message.media_duration,
            "width": message.media_width,
            "height": message.media_height,
        }
    else:
        payload["media"] = None

    return payload


class MatchmakingConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.searching_users: Dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[username] = websocket

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
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения через WebSocket для пользователя {username}: {e}")
                self.disconnect(username)


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

    async def broadcast_to_chat(self, chat_id: int, message: dict, exclude_username: str = None):
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
            logger.error(f"Ошибка отправки сообщения пользователю {username} в чате {chat_id}: {e}")
            self.disconnect(chat_id, username)


chat_manager = AnonymousChatConnectionManager()


@router.post("/start/{username}", response_model=MatchmakingStatusResponse)
async def start_matchmaking(
    username: str,
    session: AsyncSession = Depends(get_db),
) -> MatchmakingStatusResponse:
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

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
        chat_found = await find_match(session, user.id)
    except Exception as match_error:
        logger.error(f"Ошибка мгновенного матчинга для {username}: {match_error}", exc_info=True)

    queue_count = await get_matchmaking_queue_count(session, exclude_user_id=user.id)

    if chat_found:
        logger.info(f"Мгновенный матч найден в REST для {username}: чат {chat_found.id}")
        other_user_id = chat_found.user2_id if chat_found.user1_id == user.id else chat_found.user1_id

        other_user_stmt = select(User).where(User.id == other_user_id)
        other_user_result = await session.execute(other_user_stmt)
        other_user = other_user_result.scalar_one_or_none()

        payload = {
            "type": "match_found",
            "chat_id": chat_found.id,
        }

        await matchmaking_manager.send_personal_message(payload, username)

        if other_user:
            await matchmaking_manager.send_personal_message(payload, other_user.username)

        return MatchmakingStatusResponse(
            is_searching=False,
            queue_count=queue_count,
            chat_id=chat_found.id,
        )

    return MatchmakingStatusResponse(
        is_searching=True,
        queue_count=queue_count,
    )


@router.post("/stop/{username}")
async def stop_matchmaking(
    username: str,
    session: AsyncSession = Depends(get_db),
):
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

            if not user.messengers_enabled:
                await websocket.send_json({
                    "type": "error",
                    "message": "Мессенджеры недоступны. Пройдите опрос."
                })
                matchmaking_manager.disconnect(username)
                return

            if not await has_completed_profile(session, user.id):
                await websocket.send_json({
                    "type": "error",
                    "message": "Психологический профиль не завершен. Пройдите опрос."
                })
                matchmaking_manager.disconnect(username)
                return

            queue_count = await get_matchmaking_queue_count(session, exclude_user_id=user.id)
            await websocket.send_json({
                "type": "status",
                "queue_count": queue_count,
            })
            from src.db.models import MatchmakingQueue, User
            from sqlalchemy import select

            stmt = select(MatchmakingQueue).where(MatchmakingQueue.user_id == user.id)
            result = await session.execute(stmt)
            queue_entry = result.scalar_one_or_none()

            if not queue_entry or not queue_entry.is_searching:
                await join_matchmaking_queue(session, user.id)
                
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
            async def search_loop():
                try:
                    logger.info(f"Начало поиска матча для {username}")
                    first_check = True
                    while True:
                        if first_check:
                            first_check = False
                            await asyncio.sleep(0.5)
                        else:
                            await asyncio.sleep(2)

                        async with AsyncSessionLocal() as search_session:
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

                            try:
                                logger.info(f"[{username}] Попытка найти матч...")
                                chat = await find_match(search_session, user.id)
                                if chat:
                                    logger.info(f"Матч найден для {username}: чат {chat.id}")
                                    
                                    other_user_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
                                    other_user_stmt = select(User).where(User.id == other_user_id)
                                    other_user_result = await search_session.execute(other_user_stmt)
                                    other_user = other_user_result.scalar_one_or_none()
                                    
                                    await websocket.send_json({
                                        "type": "match_found",
                                        "chat_id": chat.id,
                                    })
                                    
                                    if other_user:
                                        logger.info(f"Отправка уведомления второму пользователю {other_user.username}")
                                        await matchmaking_manager.send_personal_message(
                                            {
                                                "type": "match_found",
                                                "chat_id": chat.id,
                                            },
                                            other_user.username
                                        )
                                    
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

            search_task = asyncio.create_task(search_loop())
            matchmaking_manager.searching_users[username] = search_task
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
        if search_task:
            search_task.cancel()
        
        matchmaking_manager.disconnect(username)
        
        if user:
            try:
                async with AsyncSessionLocal() as cleanup_session:
                    await leave_matchmaking_queue(cleanup_session, user.id)
                    logger.info(f"Пользователь {username} удален из очереди матчинга")
            except Exception as e:
                logger.error(f"Ошибка при очистке очереди для {username}: {e}")


@router.websocket("/chat/{chat_id}/ws/{username}")
async def anonymous_chat_websocket(websocket: WebSocket, chat_id: int, username: str):
    logger.info(f"WebSocket подключение к чату {chat_id} от пользователя {username}")
    
    user = None
    
    try:
        async with AsyncSessionLocal() as session:
            user = await get_user_by_username(session, username)
            if not user:
                logger.warning(f"Пользователь {username} не найден")
                await websocket.close(code=4004, reason="Пользователь не найден")
                return

            chat = await get_anonymous_chat(session, chat_id, user.id)
            if not chat:
                logger.warning(f"Чат {chat_id} не найден для пользователя {username}")
                await websocket.close(code=4004, reason="Чат не найден")
                return

        await chat_manager.connect(websocket, chat_id, username)

        await websocket.send_json({
            "type": "connected",
            "chat_id": chat_id,
        })
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
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
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
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
            last_msg = chat.messages[-1]
            last_message = summarize_message_text(last_msg)
            last_message_time = last_msg.created_at.isoformat()
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
            "name": other_alias,
        })

    return result


@router.get("/public-chats/{username}")
async def get_public_chats(
    username: str,
    session: AsyncSession = Depends(get_db),
):
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
            last_message = summarize_message_text(last_msg)
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

    messages = [
        build_message_payload(msg, current_user_id=user.id)
        for msg in chat.messages
    ]

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

        await chat_manager.broadcast_to_chat(
            chat_id,
            {
                "type": "new_message",
                "message": build_message_payload(message, is_mine_override=False),
            },
            exclude_username=username
        )

        return build_message_payload(message, current_user_id=user.id, is_mine_override=True)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/chat/{chat_id}/media/{username}")
async def send_anonymous_media(
    chat_id: int,
    username: str,
    media_type: Literal["photo", "video"] = Form(...),
    file: UploadFile = File(...),
    caption: str | None = Form(None),
    session: AsyncSession = Depends(get_db),
):
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    if media_type == "photo" and not user.media_auto_upload_photos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Отправка фотографий отключена в настройках.",
        )

    if media_type == "video" and not user.media_auto_upload_videos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Отправка видео отключена в настройках.",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл не указан",
        )

    ext = Path(file.filename).suffix.lower()
    if media_type == "photo" and ext not in PHOTO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый формат изображения",
        )
    if media_type == "video" and ext not in VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый формат видео",
        )

    contents = await file.read()
    size = len(contents)
    if size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пустой файл",
        )

    max_size = MAX_PHOTO_SIZE if media_type == "photo" else MAX_VIDEO_SIZE
    if size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл превышает допустимый размер",
        )

    chat_dir = CHAT_MEDIA_ROOT / str(chat_id)
    chat_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4().hex
    stored_path = chat_dir / f"{file_id}{ext}"
    with open(stored_path, "wb") as buffer:
        buffer.write(contents)

    media_url = f"/static/uploads/chat_media/{chat_id}/{stored_path.name}"
    preview_url = media_url if media_type == "photo" else None

    try:
        message = await create_anonymous_message(
            session,
            chat_id,
            user.id,
            caption,
            media_type=media_type,
            media_url=media_url,
            media_preview_url=preview_url,
            media_size=size,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    await chat_manager.broadcast_to_chat(
        chat_id,
        {
            "type": "new_message",
            "message": build_message_payload(message, is_mine_override=False),
        },
        exclude_username=username,
    )

    return build_message_payload(message, current_user_id=user.id, is_mine_override=True)


@router.post("/chat/{chat_id}/reveal/{username}")
async def reveal_chat(
    chat_id: int,
    username: str,
    session: AsyncSession = Depends(get_db),
):
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

