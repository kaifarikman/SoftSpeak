"""FastAPI приложение для ML сервиса."""
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from services.embedding import make_embedding_from_answer, load_model, is_model_loaded
from services.vector_utils import create_profile_vector_from_embeddings
from services.matching import find_best_match

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Startup: загружаем модель ДО запуска сервера
    logger.info("=" * 60)
    logger.info("Запуск ML сервиса...")
    logger.info("Загрузка модели (это может занять несколько минут)...")
    
    try:
        # Загружаем модель синхронно в executor с таймаутом
        loop = asyncio.get_event_loop()
        
        # Устанавливаем таймаут 30 минут на загрузку модели (модель большая, ~500MB)
        logger.info("Начало загрузки модели (таймаут: 30 минут)...")
        logger.info("Модель 'intfloat/multilingual-e5-base' весит ~500MB, скачивание может занять время")
        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, load_model),
                timeout=1800.0  # 30 минут
            )
            logger.info("=" * 60)
            logger.info("✓ ML модель успешно загружена и готова к использованию!")
            logger.info("=" * 60)
        except asyncio.TimeoutError:
            logger.error("=" * 60)
            logger.error("✗ ТАЙМАУТ: Загрузка модели превысила 15 минут")
            logger.error("Возможные причины:")
            logger.error("  - Медленное интернет-соединение")
            logger.error("  - Проблемы с HuggingFace")
            logger.error("  - Недостаточно ресурсов")
            logger.error("=" * 60)
            raise RuntimeError("Таймаут загрузки модели")
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"✗ КРИТИЧЕСКАЯ ОШИБКА: Не удалось загрузить модель: {e}")
        logger.error("Сервис не будет работать без модели!")
        logger.error("=" * 60)
        raise  # Прерываем запуск, если модель не загрузилась
    
    yield
    
    # Shutdown
    logger.info("Остановка ML сервиса...")


app = FastAPI(
    title="SoftSpeak ML Service",
    description="ML сервис для работы с эмбеддингами и психологическими профилями",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic схемы для запросов и ответов
class EmbeddingRequest(BaseModel):
    text: str


class EmbeddingResponse(BaseModel):
    embedding: List[float]


class ProfileVectorRequest(BaseModel):
    embeddings: List[List[float]]


class ProfileVectorResponse(BaseModel):
    vector: List[float]


class BestMatchRequest(BaseModel):
    user_vector: List[float]
    user_id: int
    other_users: List[dict]
    threshold: Optional[float] = 0.65


class BestMatchResponse(BaseModel):
    match_id: Optional[int]


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса."""
    if not is_model_loaded():
        return {
            "status": "not_ready",
            "service": "ml-service",
            "model_status": "not_loaded",
            "message": "Модель не загружена"
        }
    
    return {
        "status": "healthy",
        "service": "ml-service",
        "model_status": "loaded",
        "message": "Сервис готов к работе"
    }


@app.post("/embedding", response_model=EmbeddingResponse)
async def create_embedding_endpoint(request: EmbeddingRequest):
    """
    Создает эмбеддинг из текста ответа.
    
    Args:
        request: Запрос с текстом ответа
        
    Returns:
        Эмбеддинг в виде списка float
    """
    # Проверяем, что модель загружена
    if not is_model_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Модель еще не загружена. Попробуйте позже."
        )
    
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Текст не может быть пустым"
        )
    
    try:
        logger.info(f"Создание эмбеддинга для текста длиной {len(request.text)} символов")
        
        # Создаем эмбеддинг (синхронная операция в executor)
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None, 
            make_embedding_from_answer, 
            request.text
        )
        
        # Преобразуем в список
        embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
        
        logger.debug(f"Эмбеддинг успешно создан, размер: {len(embedding_list)}")
        return EmbeddingResponse(embedding=embedding_list)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при создании эмбеддинга: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании эмбеддинга: {str(e)}"
        )


@app.post("/profile-vector", response_model=ProfileVectorResponse)
async def create_profile_vector_endpoint(request: ProfileVectorRequest):
    """
    Создает финальный вектор профиля из эмбеддингов ответов.
    
    Args:
        request: Запрос со списком эмбеддингов
        
    Returns:
        Нормализованный вектор профиля
    """
    if not request.embeddings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Список эмбеддингов не может быть пустым"
        )
    
    try:
        # Создаем вектор профиля (синхронная операция, быстрая)
        loop = asyncio.get_event_loop()
        vector = await loop.run_in_executor(
            None,
            create_profile_vector_from_embeddings,
            request.embeddings
        )
        
        return ProfileVectorResponse(vector=vector)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при создании вектора профиля: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании вектора профиля: {str(e)}"
        )


@app.post("/best-match", response_model=BestMatchResponse)
async def find_best_match_endpoint(request: BestMatchRequest):
    """
    Находит пользователя с наиболее похожим психологическим профилем.
    
    Args:
        request: Запрос с вектором пользователя, его ID и списком других пользователей
        
    Returns:
        ID пользователя с лучшим совпадением или None
    """
    if not request.other_users:
        return BestMatchResponse(match_id=None)
    
    try:
        # Находим лучшее совпадение (синхронная операция)
        loop = asyncio.get_event_loop()
        match_id = await loop.run_in_executor(
            None,
            find_best_match,
            request.user_vector,
            request.user_id,
            request.other_users,
            request.threshold
        )
        
        return BestMatchResponse(match_id=match_id)
    
    except Exception as e:
        logger.error(f"Ошибка при поиске совпадения: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при поиске совпадения: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
