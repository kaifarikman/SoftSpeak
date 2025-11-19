"""WebSocket эндпоинт для опроса."""
import json
import logging
import asyncio
from typing import Dict

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import AsyncSessionLocal
from src.db.crud.auth import get_user_by_username
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


async def create_profile_with_embeddings(session: AsyncSession, user_id: int, username: str) -> bool:
    """
    Создает психологический профиль с реальными эмбеддингами.
    
    Args:
        session: Сессия БД
        user_id: ID пользователя
        username: Имя пользователя (для логов)
        
    Returns:
        True если профиль создан успешно, False в случае ошибки
    """
    try:
        logger.info(f"Начало создания профиля для {username}")
        
        # Получаем все ответы пользователя
        answers = await get_user_answers(session, user_id)
        if len(answers) < 10:
            logger.error(f"Недостаточно ответов для создания профиля: {len(answers)}/10")
            return False
        
        logger.info(f"Создание эмбеддингов для {len(answers)} ответов...")
        embeddings_created = 0
        embeddings = []
        
        # Создаем эмбеддинги для каждого ответа
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
            except Exception as e:
                logger.error(f"Ошибка создания эмбеддинга для ответа {answer.id}: {e}", exc_info=True)
                return False
        
        await session.commit()
        logger.info(f"Все эмбеддинги созданы для {username}")
        
        # Создаем вектор профиля
        if len(embeddings) >= 10:
            logger.info(f"Создание вектора профиля для {username}...")
            profile_vector = await create_profile_vector(embeddings)
            
            # Удаляем старый профиль, если есть
            old_profile = await get_psychological_profile(session, user_id)
            if old_profile:
                await session.delete(old_profile)
            
            # Создаем новый профиль
            await create_psychological_profile(session, user_id, profile_vector)
            await session.commit()
            logger.info(f"✓ Профиль успешно создан для {username}")
            return True
        else:
            logger.error(f"Недостаточно эмбеддингов: {len(embeddings)}/10")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка создания профиля для {username}: {e}", exc_info=True)
        return False


class ConnectionManager:
    """Менеджер WebSocket соединений."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, username: str):
        """Подключает пользователя."""
        await websocket.accept()
        self.active_connections[username] = websocket

    def disconnect(self, username: str):
        """Отключает пользователя."""
        if username in self.active_connections:
            del self.active_connections[username]

    async def send_personal_message(self, message: dict, username: str):
        """Отправляет сообщение конкретному пользователю."""
        if username in self.active_connections:
            websocket = self.active_connections[username]
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Ошибка отправки сообщения пользователю {username}: {e}")
                self.disconnect(username)


manager = ConnectionManager()


async def websocket_survey_endpoint(websocket: WebSocket, username: str):
    """WebSocket эндпоинт для опроса."""
    await manager.connect(websocket, username)

    # Создаем сессию БД напрямую (в WebSocket нет dependency injection)
    async with AsyncSessionLocal() as session:
        try:
            # Проверяем пользователя
            user = await get_user_by_username(session, username)
            if not user:
                await websocket.send_json({
                    "type": "error",
                    "message": "Пользователь не найден"
                })
                manager.disconnect(username)
                return

            # Проверяем, завершен ли профиль
            profile_completed = await has_completed_profile(session, user.id)
            if profile_completed:
                await websocket.send_json({
                    "type": "survey_completed",
                    "message": "Опрос уже завершен"
                })
                manager.disconnect(username)
                return

            # Восстанавливаем историю опроса (все предыдущие вопросы и ответы)
            answers = await get_user_answers(session, user.id)
            if answers:
                # Отправляем историю вопросов и ответов
                for answer in answers:
                    await session.refresh(answer.question, ["category"])
                    # Отправляем вопрос (только текст, без категории)
                    await websocket.send_json({
                        "type": "question",
                        "question": {
                            "id": answer.question.id,
                            "category_id": answer.question.category_id,
                            "text": answer.question.text,
                        },
                        "current_question_number": 0,  # Для истории не важно
                        "total_questions": 10,
                        "is_history": True,  # Флаг, что это история
                    })
                    # Отправляем ответ
                    await websocket.send_json({
                        "type": "answer_history",
                        "answer_text": answer.answer_text,
                        "created_at": answer.created_at.isoformat(),
                    })

            # Отправляем следующий вопрос автоматически при подключении
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
                # Нет следующего вопроса - проверяем, все ли вопросы отвечены
                answers_count = await get_user_answers_count(session, user.id)
                
                if answers_count == 0:
                    # Пользователь еще не начал опрос, но нет вопросов в базе
                    await websocket.send_json({
                        "type": "error",
                        "message": "Нет доступных вопросов для опроса. Обратитесь к администратору."
                    })
                    manager.disconnect(username)
                    try:
                        await websocket.close(code=1000)
                    except:
                        pass
                    return
                
                # Есть ответы, проверяем профиль
                profile_completed = await has_completed_profile(session, user.id)
                if not profile_completed and answers_count >= 10:
                    # Создаем профиль синхронно с реальными эмбеддингами
                    logger.info(f"Восстановление: создание профиля для пользователя {username}")
                    
                    # Создаем профиль с эмбеддингами
                    profile_created = await create_profile_with_embeddings(session, user.id, username)
                    
                    if profile_created:
                        # Активируем мессенджеры только после успешного создания профиля
                        user.messengers_enabled = True
                        await session.commit()
                        logger.info(f"✓ Профиль создан, мессенджеры активированы для {username}")
                    else:
                        logger.error(f"✗ Не удалось создать профиль для {username}")
                    
                    # Сохраняем вопросы и ответы в чат
                    try:
                        chat = await get_or_create_active_chat(session, user.id)
                        answers = await get_user_answers(session, user.id)
                        
                        # Сохраняем все вопросы и ответы как сообщения в чат
                        for answer in answers:
                            await session.refresh(answer.question)
                            # Сохраняем вопрос (от бота)
                            await create_message(
                                session,
                                chat.id,
                                answer.question.text,
                                is_from_user=False
                            )
                            # Сохраняем ответ (от пользователя)
                            await create_message(
                                session,
                                chat.id,
                                answer.answer_text,
                                is_from_user=True
                            )
                        
                        await session.commit()
                        logger.info(f"Вопросы и ответы сохранены в чат для пользователя {username}")
                    except Exception as e:
                        logger.error(f"Ошибка сохранения вопросов и ответов в чат: {e}", exc_info=True)
                
                # Отправляем сообщение о завершении только если профиль создан
                if await has_completed_profile(session, user.id):
                    await websocket.send_json({
                        "type": "survey_completed",
                        "message": "Опрос завершен! Ваш психологический портрет создан."
                    })
                    manager.disconnect(username)
                    try:
                        await websocket.close(code=1000)  # Нормальное закрытие
                    except:
                        pass
                    return
                else:
                    # Есть ответы, но меньше 10 или профиль не создан - ошибка
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Ошибка: отвечено {answers_count} из 10 вопросов, но следующий вопрос не найден. Возможно, в базе недостаточно активных вопросов или не удалось создать эмбеддинги."
                    })
                    manager.disconnect(username)
                    try:
                        await websocket.close(code=1000)
                    except:
                        pass
                    return

            # Обрабатываем сообщения от клиента
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

                    # Сохраняем ответ БЕЗ эмбеддинга - эмбеддинги создадим после завершения опроса
                    answer = await save_user_answer(
                        session,
                        user.id,
                        question_id,
                        answer_text,
                        embedding=None,  # Эмбеддинг создадим позже
                    )
                    await session.commit()
                    logger.info(f"Ответ сохранен для пользователя {username}, вопрос {question_id}")

                    # Получаем следующий вопрос
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
                        # Все вопросы отвечены - создаем профиль синхронно
                        profile_completed = await has_completed_profile(session, user.id)
                        if not profile_completed:
                            answers = await get_user_answers(session, user.id)
                            logger.info(f"Опрос завершен для пользователя {username}, ответов: {len(answers)}")
                            
                            if len(answers) >= 10:
                                # Создаем профиль с реальными эмбеддингами
                                logger.info(f"Создание профиля для {username}")
                                
                                profile_created = await create_profile_with_embeddings(session, user.id, username)
                                
                                if profile_created:
                                    # Активируем мессенджеры только после успешного создания профиля
                                    user.messengers_enabled = True
                                    await session.commit()
                                    logger.info(f"✓ Профиль создан, мессенджеры активированы для {username}")
                                else:
                                    logger.error(f"✗ Не удалось создать профиль для {username}")
                                    await websocket.send_json({
                                        "type": "error",
                                        "message": "Не удалось создать психологический профиль. ML сервис недоступен."
                                    })
                                    manager.disconnect(username)
                                    return
                            
                            # Сохраняем вопросы и ответы в чат
                            try:
                                chat = await get_or_create_active_chat(session, user.id)
                                answers = await get_user_answers(session, user.id)
                                
                                # Сохраняем все вопросы и ответы как сообщения в чат
                                for answer in answers:
                                    await session.refresh(answer.question)
                                    # Сохраняем вопрос (от бота)
                                    await create_message(
                                        session,
                                        chat.id,
                                        answer.question.text,
                                        is_from_user=False
                                    )
                                    # Сохраняем ответ (от пользователя)
                                    await create_message(
                                        session,
                                        chat.id,
                                        answer.answer_text,
                                        is_from_user=True
                                    )
                                
                                await session.commit()
                                logger.info(f"Вопросы и ответы сохранены в чат для пользователя {username}")
                            except Exception as e:
                                logger.error(f"Ошибка сохранения вопросов и ответов в чат: {e}", exc_info=True)
                        
                        await websocket.send_json({
                            "type": "survey_completed",
                            "message": "Опрос завершен! Ваш психологический портрет создан."
                        })
                        manager.disconnect(username)
                        try:
                            await websocket.close(code=1000)  # Нормальное закрытие
                        except:
                            pass
                        break

                elif message.get("type") == "get_current_question":
                    # Запрос текущего вопроса (для восстановления при перезагрузке)
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
                        # Все вопросы отвечены
                        await websocket.send_json({
                            "type": "survey_completed",
                            "message": "Опрос завершен"
                        })
                        manager.disconnect(username)
                        try:
                            await websocket.close(code=1000)  # Нормальное закрытие
                        except:
                            pass
                        break

        except WebSocketDisconnect:
            manager.disconnect(username)
            await session.rollback()
            return
        except Exception as e:
            print(f"Ошибка в WebSocket: {e}")
            import traceback
            traceback.print_exc()
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Ошибка сервера: {str(e)}"
                })
            except:
                pass
            await session.rollback()
            manager.disconnect(username)
            return

