"""Интеграция с ML сервисом для работы с эмбеддингами."""
import logging
import httpx
import os
import asyncio
from typing import List, Optional, Callable, Any

logger = logging.getLogger(__name__)

# URL ML сервиса
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml-service:8001")

# Размерность вектора профиля
EMBEDDING_DIM = 768

# Глобальный HTTP клиент
_http_client: Optional[httpx.AsyncClient] = None

# Настройки retry
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0  # секунды
MAX_RETRY_DELAY = 10.0  # секунды


def get_http_client() -> httpx.AsyncClient:
    """Получает или создает HTTP клиент для запросов к ML сервису."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client


async def _retry_with_backoff(
    func: Callable,
    operation_name: str,
    *args,
    **kwargs
) -> Any:
    """
    Выполняет функцию с повторными попытками и экспоненциальной задержкой.
    
    Args:
        func: Асинхронная функция для выполнения
        operation_name: Название операции для логирования
        *args, **kwargs: Аргументы для функции
        
    Returns:
        Результат выполнения функции
        
    Raises:
        RuntimeError: Если все попытки исчерпаны
    """
    last_exception = None
    
    for attempt in range(MAX_RETRIES):
        try:
            return await func(*args, **kwargs)
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            last_exception = e
            
            # Не повторяем для клиентских ошибок (4xx), кроме таймаутов
            if isinstance(e, httpx.HTTPStatusError):
                if 400 <= e.response.status_code < 500:
                    logger.error(f"{operation_name}: Клиентская ошибка {e.response.status_code}, не повторяем")
                    raise
            
            if attempt < MAX_RETRIES - 1:
                # Экспоненциальная задержка: 1s, 2s, 4s
                delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                logger.warning(
                    f"{operation_name}: Попытка {attempt + 1}/{MAX_RETRIES} не удалась. "
                    f"Повтор через {delay:.1f}с. Ошибка: {str(e)}"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"{operation_name}: Все {MAX_RETRIES} попытки исчерпаны")
        except Exception as e:
            # Для других ошибок не повторяем
            logger.error(f"{operation_name}: Неожиданная ошибка: {e}", exc_info=True)
            raise
    
    # Если дошли сюда, все попытки исчерпаны
    raise RuntimeError(f"{operation_name}: Не удалось выполнить операцию после {MAX_RETRIES} попыток: {str(last_exception)}")


async def create_embedding(text: str) -> List[float]:
    """
    Создает эмбеддинг из текста через ML сервис.
    
    Args:
        text: Текст ответа пользователя
        
    Returns:
        Нормализованный вектор эмбеддинга
        
    Raises:
        ValueError: Если текст пустой
        RuntimeError: Если ML сервис недоступен
    """
    if not text or not text.strip():
        raise ValueError("Ответ не может быть пустым")
    
    logger.info(f"Запрос эмбеддинга для текста длиной {len(text)} символов")
    
    async def _make_request():
        client = get_http_client()
        response = await client.post(
            f"{ML_SERVICE_URL}/embedding",
            json={"text": text},
        )
        response.raise_for_status()
        
        data = response.json()
        embedding = data.get("embedding")
        
        if not embedding:
            raise RuntimeError("ML сервис вернул пустой эмбеддинг")
        
        # Валидация размера эмбеддинга
        if len(embedding) != EMBEDDING_DIM:
            raise ValueError(
                f"Неверная размерность эмбеддинга: ожидалось {EMBEDDING_DIM}, "
                f"получено {len(embedding)}"
            )
        
        logger.info(f"Эмбеддинг получен, размер: {len(embedding)}")
        return embedding
    
    return await _retry_with_backoff(_make_request, "create_embedding")


async def create_profile_vector(embeddings: List[List[float]]) -> List[float]:
    """
    Создает финальный вектор профиля из векторов ответов через ML сервис.
    
    Args:
        embeddings: Список векторов ответов
        
    Returns:
        Нормализованный вектор профиля
        
    Raises:
        ValueError: Если список эмбеддингов пустой или размерность неверная
        RuntimeError: Если ML сервис недоступен
    """
    if not embeddings:
        raise ValueError("Список векторов не может быть пустым")
    
    # Валидация размерности всех эмбеддингов
    for i, emb in enumerate(embeddings):
        if len(emb) != EMBEDDING_DIM:
            raise ValueError(
                f"Неверная размерность эмбеддинга #{i}: ожидалось {EMBEDDING_DIM}, "
                f"получено {len(emb)}"
            )
    
    logger.info(f"Создание вектора профиля из {len(embeddings)} эмбеддингов")
    
    async def _make_request():
        client = get_http_client()
        response = await client.post(
            f"{ML_SERVICE_URL}/profile-vector",
            json={"embeddings": embeddings},
        )
        response.raise_for_status()
        
        data = response.json()
        profile_vector = data.get("vector")
        
        if not profile_vector:
            raise RuntimeError("ML сервис вернул пустой вектор профиля")
        
        # Валидация размера вектора профиля
        if len(profile_vector) != EMBEDDING_DIM:
            raise ValueError(
                f"Неверная размерность вектора профиля: ожидалось {EMBEDDING_DIM}, "
                f"получено {len(profile_vector)}"
            )
        
        logger.info(f"Вектор профиля создан, размер: {len(profile_vector)}")
        return profile_vector
    
    return await _retry_with_backoff(_make_request, "create_profile_vector")


async def find_best_match(
    user_vector: List[float],
    user_id: int,
    other_users: List[dict],
    threshold: Optional[float] = None,
) -> Optional[int]:
    """
    Находит пользователя с наиболее похожим психологическим профилем через ML сервис.
    
    Args:
        user_vector: Вектор психологического профиля текущего пользователя
        user_id: ID текущего пользователя
        other_users: Список словарей с ключами 'id' и 'profile_vector'
        threshold: Порог similarity (0-1). Если None, используется из конфига
        
    Returns:
        ID пользователя с лучшим совпадением или None, если нет других пользователей
        
    Raises:
        RuntimeError: Если ML сервис недоступен
    """
    if not other_users:
        logger.info("Нет других пользователей для сравнения")
        return None
    
    # Используем threshold из конфига, если не передан явно
    if threshold is None:
        from src.core.config import settings
        threshold = settings.match_similarity_threshold
    
    logger.info(f"Поиск лучшего совпадения среди {len(other_users)} пользователей (threshold: {threshold})")
    
    async def _make_request():
        client = get_http_client()
        response = await client.post(
            f"{ML_SERVICE_URL}/best-match",
            json={
                "user_vector": user_vector,
                "user_id": user_id,
                "other_users": other_users,
                "threshold": threshold,
            },
        )
        response.raise_for_status()
        
        data = response.json()
        match_id = data.get("match_id")
        
        if match_id:
            logger.info(f"Найден лучший матч: пользователь {match_id}")
        else:
            logger.info("Не найдено подходящих совпадений")
        
        return match_id
    
    return await _retry_with_backoff(_make_request, "find_best_match")
