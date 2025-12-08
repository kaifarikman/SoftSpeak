import json
import logging
import asyncio
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import AsyncSessionLocal
from src.db.crud.auth import get_user_by_email
from src.db.crud.psychological import (
    get_next_question_for_user,
    save_user_answer,
    get_user_answers_count,
    get_user_answers,
    create_psychological_profile,
    get_psychological_profile,
    has_completed_profile,
)
from src.db.crud.chat import get_or_create_active_chat, create_message
from src.services.vector_utils import create_embedding, create_profile_vector

logger = logging.getLogger(__name__)

_pending_profiles_queue: List[Tuple[int, str, datetime]] = []
_queue_lock: Optional[asyncio.Lock] = None


def _get_queue_lock() -> asyncio.Lock:
    global _queue_lock
    if _queue_lock is None:
        _queue_lock = asyncio.Lock()
    return _queue_lock


async def _retry_pending_profiles():
    global _pending_profiles_queue
    
    while True:
        await asyncio.sleep(60)
        
        if not _pending_profiles_queue:
            continue
        
        async with _get_queue_lock():
            queue_copy = _pending_profiles_queue.copy()
            _pending_profiles_queue.clear()
        
        for user_id, email, timestamp in queue_copy:
            try:
                async with AsyncSessionLocal() as session:
                    profile_created = await create_profile_with_embeddings(session, user_id, email)
                    if profile_created:
                        logger.info(f"✓ Отложенный профиль успешно создан для {email}")
                    else:
                        if (datetime.now(timezone.utc) - timestamp).total_seconds() < 3600:
                            async with _get_queue_lock():
                                _pending_profiles_queue.append((user_id, email, timestamp))
            except Exception as e:
                logger.error(f"Ошибка при обработке отложенного профиля для {email}: {e}")
                if (datetime.now(timezone.utc) - timestamp).total_seconds() < 3600:
                    async with _get_queue_lock():
                        _pending_profiles_queue.append((user_id, email, timestamp))


_retry_task = None


def start_retry_task():
    global _retry_task
    if _retry_task is None or _retry_task.done():
        _retry_task = asyncio.create_task(_retry_pending_profiles())
        logger.info("Запущена фоновая задача для обработки отложенных профилей")


async def create_profile_with_embeddings(session: AsyncSession, user_id: int, email: str) -> bool:
    try:
        logger.info(f"Начало создания профиля для {email}")
        
        answers = await get_user_answers(session, user_id)
        if len(answers) < 10:
            logger.error(f"Недостаточно ответов для создания профиля: {len(answers)}/10")
            return False
        
        logger.info(f"Создание эмбеддингов для {len(answers)} ответов...")
        embeddings_created = 0
        embeddings = []
        
        for answer in answers:
            try:
                if not answer.embedding:
                    logger.info(f"Создание эмбеддинга для ответа {answer.id}...")
                    embedding_list = await create_embedding(answer.answer_text)
                    answer.embedding = embedding_list
                    session.add(answer)
                    embeddings.append(embedding_list)
                    embeddings_created += 1
                    logger.info(f"Эмбеддинг создан ({embeddings_created}/{len(answers)})")
                else:
                    embeddings.append(answer.embedding)
            except RuntimeError as e:
                error_msg = str(e).lower()
                if "ml сервис" in error_msg or "не удалось подключиться" in error_msg or "недоступен" in error_msg:
                    logger.warning(f"ML-сервис недоступен для ответа {answer.id}, добавляем в очередь")
                    async with _get_queue_lock():
                        _pending_profiles_queue.append((user_id, email, datetime.now(timezone.utc)))
                    start_retry_task()
                    return False
                else:
                    logger.error(f"Ошибка создания эмбеддинга для ответа {answer.id}: {e}", exc_info=True)
                    return False
            except Exception as e:
                logger.error(f"Ошибка создания эмбеддинга для ответа {answer.id}: {e}", exc_info=True)
                return False
        
        await session.commit()
        logger.info(f"Все эмбеддинги созданы для {email}")
        
        if len(embeddings) >= 10:
            logger.info(f"Создание вектора профиля для {email}...")
            profile_vector = await create_profile_vector(embeddings)
            
            old_profile = await get_psychological_profile(session, user_id)
            if old_profile:
                await session.delete(old_profile)
            
            await create_psychological_profile(session, user_id, profile_vector)
            await session.commit()
            logger.info(f"✓ Профиль успешно создан для {email}")
            return True
        else:
            logger.error(f"Недостаточно эмбеддингов: {len(embeddings)}/10")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка создания профиля для {email}: {e}", exc_info=True)
        return False


class ConnectionManager:

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, email: str):
        await websocket.accept()
        self.active_connections[email] = websocket

    def disconnect(self, email: str):
        if email in self.active_connections:
            del self.active_connections[email]

    async def send_personal_message(self, message: dict, email: str):
        if email in self.active_connections:
            websocket = self.active_connections[email]
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Ошибка отправки сообщения пользователю {email}: {e}")
                self.disconnect(email)


manager = ConnectionManager()


async def websocket_survey_endpoint(websocket: WebSocket, email: str):
    await manager.connect(websocket, email)

    async with AsyncSessionLocal() as session:
        try:
            user = await get_user_by_email(session, email)
            if not user:
                await websocket.send_json({
                    "type": "error",
                    "message": "Пользователь не найден"
                })
                manager.disconnect(email)
                return

            # Проверяем, не забанен ли пользователь
            if user.is_banned:
                logger.warning(f"Пользователь {email} забанен, отключение WebSocket survey")
                await websocket.send_json({
                    "type": "error",
                    "message": "Ваш аккаунт заблокирован администратором. Доступ запрещен."
                })
                manager.disconnect(email)
                await websocket.close(code=4003, reason="Аккаунт заблокирован")
                return

            profile_completed = await has_completed_profile(session, user.id)
            if profile_completed:
                await websocket.send_json({
                    "type": "survey_completed",
                    "message": "Опрос уже завершен"
                })
                manager.disconnect(email)
                return

            answers = await get_user_answers(session, user.id)
            if answers:
                for answer in answers:
                    await session.refresh(answer.question, ["category"])
                    await websocket.send_json({
                        "type": "question",
                        "question": {
                            "id": answer.question.id,
                            "category_id": answer.question.category_id,
                            "text": answer.question.text,
                        },
                        "current_question_number": 0,
                        "total_questions": 10,
                        "is_history": True,
                    })
                    await websocket.send_json({
                        "type": "answer_history",
                        "answer_text": answer.answer_text,
                        "created_at": answer.created_at.isoformat(),
                    })

            result = await get_next_question_for_user(session, user.id)
            if result:
                question, current_number, total_count = result
                await session.refresh(question, ["category"])
                
                await websocket.send_json({
                    "type": "question",
                    "question": {
                        "id": question.id,
                        "category_id": question.category_id,
                        "text": question.text,
                    },
                    "current_question_number": current_number,
                    "total_questions": total_count,
                })
            else:
                answers_count = await get_user_answers_count(session, user.id)
                
                if answers_count == 0:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Нет доступных вопросов для опроса. Обратитесь к администратору."
                    })
                    manager.disconnect(email)
                    try:
                        await websocket.close(code=1000)
                    except:
                        pass
                    return
                
                profile_completed = await has_completed_profile(session, user.id)
                if not profile_completed and answers_count >= 10:
                    logger.info(f"Восстановление: создание профиля для пользователя {email}")
                    
                    profile_created = await create_profile_with_embeddings(session, user.id, email)
                    
                    if profile_created:
                        user.messengers_enabled = True
                        user.ai_enabled = False  # Отключаем AI чат после завершения опроса
                        await session.commit()
                        logger.info(f"✓ Профиль создан, мессенджеры активированы, AI чат отключен для {email}")
                    else:
                        logger.error(f"✗ Не удалось создать профиль для {email}")
                    
                    try:
                        chat = await get_or_create_active_chat(session, user.id)
                        answers = await get_user_answers(session, user.id)
                        
                        for answer in answers:
                            await session.refresh(answer.question)
                            await create_message(
                                session,
                                chat.id,
                                answer.question.text,
                                is_from_user=False
                            )
                            await create_message(
                                session,
                                chat.id,
                                answer.answer_text,
                                is_from_user=True
                            )
                        
                        # Добавляем сообщение о завершении опроса в БД
                        await create_message(
                            session,
                            chat.id,
                            "Опрос завершен! Ваш психологический портрет создан.",
                            is_from_user=False
                        )
                        await session.commit()
                        logger.info(f"Вопросы и ответы сохранены в чат для пользователя {email}")
                    except Exception as e:
                        logger.error(f"Ошибка сохранения вопросов и ответов в чат: {e}", exc_info=True)
                
                if await has_completed_profile(session, user.id):
                    await websocket.send_json({
                        "type": "survey_completed",
                        "message": "Опрос завершен! Ваш психологический портрет создан."
                    })
                    manager.disconnect(email)
                    try:
                        await websocket.close(code=1000)
                    except:
                        pass
                    return
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Ошибка: отвечено {answers_count} из 10 вопросов, но следующий вопрос не найден. Возможно, в базе недостаточно активных вопросов или не удалось создать эмбеддинги."
                    })
                    manager.disconnect(email)
                    try:
                        await websocket.close(code=1000)
                    except:
                        pass
                    return

            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Неверный формат сообщения"
                    })
                    continue

                if message.get("type") == "answer":
                    answer_text = message.get("answer_text", "").strip()
                    question_id = message.get("question_id")

                    if not answer_text or not question_id:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Неверные данные ответа"
                        })
                        continue

                    answer = await save_user_answer(
                        session,
                        user.id,
                        question_id,
                        answer_text,
                        embedding=None, 
                    )
                    await session.commit()
                    logger.info(f"Ответ сохранен для пользователя {email}, вопрос {question_id}")

                    result = await get_next_question_for_user(session, user.id)
                    if result:
                        question, current_number, total_count = result
                        await session.refresh(question, ["category"])
                        
                        await websocket.send_json({
                            "type": "question",
                            "question": {
                                "id": question.id,
                                "category_id": question.category_id,
                                "text": question.text,
                                "category": {
                                    "id": question.category.id,
                                    "name": question.category.name,
                                    "description": question.category.description,
                                }
                            },
                            "current_question_number": current_number,
                            "total_questions": total_count,
                        })
                    else:
                        profile_completed = await has_completed_profile(session, user.id)
                        if not profile_completed:
                            answers = await get_user_answers(session, user.id)
                            logger.info(f"Опрос завершен для пользователя {email}, ответов: {len(answers)}")
                            
                            if len(answers) >= 10:
                                logger.info(f"Создание профиля для {email}")
                                
                                try:
                                    profile_created = await create_profile_with_embeddings(session, user.id, email)
                                except RuntimeError as e:
                                    error_msg = str(e).lower()
                                    if "ml сервис" in error_msg or "не удалось подключиться" in error_msg:
                                        await websocket.send_json({
                                            "type": "error",
                                            "message": "Сервис создания профиля временно недоступен. Ваши ответы сохранены, профиль будет создан автоматически, когда сервис станет доступен."
                                        })
                                        logger.warning(f"ML-сервис недоступен для {email}, ответы сохранены")
                                    profile_created = False
                                
                                if profile_created:
                                    user.messengers_enabled = True
                                    user.ai_enabled = False  # Отключаем AI чат после завершения опроса
                                    await session.commit()
                                    logger.info(f"✓ Профиль создан, мессенджеры активированы, AI чат отключен для {email}")
                                else:
                                    logger.error(f"✗ Не удалось создать профиль для {email}")
                                    await websocket.send_json({
                                        "type": "error",
                                        "message": "Не удалось создать психологический профиль. ML сервис недоступен."
                                    })
                                    manager.disconnect(email)
                                    return
                            
                            try:
                                chat = await get_or_create_active_chat(session, user.id)
                                answers = await get_user_answers(session, user.id)
                                
                                for answer in answers:
                                    await session.refresh(answer.question)
                                    await create_message(
                                        session,
                                        chat.id,
                                        answer.question.text,
                                        is_from_user=False
                                    )
                                    await create_message(
                                        session,
                                        chat.id,
                                        answer.answer_text,
                                        is_from_user=True
                                    )
                                
                                # Добавляем сообщение о завершении опроса в БД
                                await create_message(
                                    session,
                                    chat.id,
                                    "Опрос завершен! Ваш психологический портрет создан.",
                                    is_from_user=False
                                )
                                await session.commit()
                                logger.info(f"Вопросы и ответы сохранены в чат для пользователя {email}")
                            except Exception as e:
                                logger.error(f"Ошибка сохранения вопросов и ответов в чат: {e}", exc_info=True)
                        
                        await websocket.send_json({
                            "type": "survey_completed",
                            "message": "Опрос завершен! Ваш психологический портрет создан."
                        })
                        manager.disconnect(email)
                        try:
                            await websocket.close(code=1000)
                        except:
                            pass
                        break

                elif message.get("type") == "get_current_question":
                    result = await get_next_question_for_user(session, user.id)
                    if result:
                        question, current_number, total_count = result
                        await session.refresh(question, ["category"])
                        
                        await websocket.send_json({
                            "type": "question",
                            "question": {
                                "id": question.id,
                                "category_id": question.category_id,
                                "text": question.text,
                                "category": {
                                    "id": question.category.id,
                                    "name": question.category.name,
                                    "description": question.category.description,
                                }
                            },
                            "current_question_number": current_number,
                            "total_questions": total_count,
                        })
                    else:
                        await websocket.send_json({
                            "type": "survey_completed",
                            "message": "Опрос завершен"
                        })
                        manager.disconnect(email)
                        try:
                            await websocket.close(code=1000)
                        except:
                            pass
                        break

        except WebSocketDisconnect:
            logger.info(f"WebSocket отключен для пользователя {email} (опрос)")
            manager.disconnect(email)
            await session.rollback()
            return
        except Exception as e:
            logger.error(f"Ошибка в WebSocket опроса для {email}: {e}", exc_info=True)
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Ошибка сервера: {str(e)}"
                })
            except Exception:
                logger.warning(f"Не удалось отправить сообщение об ошибке пользователю {email}")
            await session.rollback()
            manager.disconnect(email)
            return
        finally:
            try:
                manager.disconnect(email)
            except Exception as e:
                logger.error(f"Ошибка при отключении пользователя {email} из менеджера опроса: {e}")
            
            try:
                if websocket.client_state.name != "DISCONNECTED":
                    await websocket.close(code=1000)
            except Exception as e:
                logger.warning(f"Ошибка при закрытии WebSocket для {email}: {e}")

