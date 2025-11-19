"""Интеграция с ML сервисом для работы с эмбеддингами."""
import logging
import httpx
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

# URL ML сервиса
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml-service:8001")

# Размерность вектора профиля
EMBEDDING_DIM = 768

# Глобальный HTTP клиент
_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """Получает или создает HTTP клиент для запросов к ML сервису."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client


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
    
    try:
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
        
        logger.info(f"Эмбеддинг получен, размер: {len(embedding)}")
        return embedding
    
    except httpx.HTTPStatusError as e:
        logger.error(f"Ошибка HTTP при запросе к ML сервису: {e.response.status_code} - {e.response.text}")
        raise RuntimeError(f"ML сервис вернул ошибку: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"Ошибка подключения к ML сервису: {e}")
        raise RuntimeError("Не удалось подключиться к ML сервису")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при запросе к ML сервису: {e}", exc_info=True)
        raise RuntimeError(f"Ошибка при создании эмбеддинга: {str(e)}")


async def create_profile_vector(embeddings: List[List[float]]) -> List[float]:
    """
    Создает финальный вектор профиля из векторов ответов через ML сервис.
    
    Args:
        embeddings: Список векторов ответов
        
    Returns:
        Нормализованный вектор профиля
        
    Raises:
        ValueError: Если список эмбеддингов пустой
        RuntimeError: Если ML сервис недоступен
    """
    if not embeddings:
        raise ValueError("Список векторов не может быть пустым")
    
    logger.info(f"Создание вектора профиля из {len(embeddings)} эмбеддингов")
    
    try:
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
        
        logger.info(f"Вектор профиля создан, размер: {len(profile_vector)}")
        return profile_vector
    
    except httpx.HTTPStatusError as e:
        logger.error(f"Ошибка HTTP при запросе к ML сервису: {e.response.status_code} - {e.response.text}")
        raise RuntimeError(f"ML сервис вернул ошибку: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"Ошибка подключения к ML сервису: {e}")
        raise RuntimeError("Не удалось подключиться к ML сервису")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при запросе к ML сервису: {e}", exc_info=True)
        raise RuntimeError(f"Ошибка при создании вектора профиля: {str(e)}")


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
    
    try:
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
    
    except httpx.HTTPStatusError as e:
        logger.error(f"Ошибка HTTP при запросе к ML сервису: {e.response.status_code} - {e.response.text}")
        raise RuntimeError(f"ML сервис вернул ошибку: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"Ошибка подключения к ML сервису: {e}")
        raise RuntimeError("Не удалось подключиться к ML сервису")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при запросе к ML сервису: {e}", exc_info=True)
        raise RuntimeError(f"Ошибка при поиске совпадения: {str(e)}")
