import asyncio
import logging
from typing import Dict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


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
            except Exception:
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


matchmaking_manager = MatchmakingConnectionManager()
chat_manager = AnonymousChatConnectionManager()
