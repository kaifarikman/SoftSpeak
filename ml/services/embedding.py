"""Создание эмбеддингов из текста ответов."""
import torch
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

from .normalize_text import normalize_text

logger = logging.getLogger(__name__)

MODEL_NAME = "intfloat/multilingual-e5-base"
device = 'cuda' if torch.cuda.is_available() else 'cpu'
_model_st: SentenceTransformer | None = None


def load_model() -> SentenceTransformer:
    """
    Загружает модель SentenceTransformer.
    Должна быть вызвана один раз при старте приложения.
    
    Returns:
        Загруженная модель
        
    Raises:
        RuntimeError: Если не удалось загрузить модель
    """
    global _model_st
    
    if _model_st is not None:
        logger.info("Модель уже загружена")
        return _model_st
    
    try:
        import os
        from pathlib import Path
        
        logger.info(f"Загрузка модели '{MODEL_NAME}' на устройство: {device}")
        logger.info("Это может занять несколько минут при первом запуске...")
        
        # Используем кэш из переменной окружения или домашнюю директорию
        cache_base = os.environ.get('HF_HOME') or os.environ.get('TRANSFORMERS_CACHE') or str(Path.home() / ".cache" / "huggingface")
        cache_dir = Path(cache_base) / "hub"
        
        logger.info(f"Используется кэш: {cache_dir}")
        
        # Создаем директорию кэша, если её нет
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Очищаем неполные загрузки
        if cache_dir.exists():
            incomplete_files = list(cache_dir.rglob("*.incomplete"))
            if incomplete_files:
                logger.info(f"Найдено {len(incomplete_files)} неполных загрузок, очищаем...")
                for incomplete_file in incomplete_files:
                    try:
                        incomplete_file.unlink()
                        logger.info(f"Удален неполный файл: {incomplete_file}")
                    except Exception as e:
                        logger.warning(f"Не удалось удалить {incomplete_file}: {e}")
        
        logger.info("Начинаем загрузку модели из HuggingFace...")
        logger.info("Модель весит ~500MB, это может занять 5-15 минут в зависимости от скорости интернета")
        
        # Устанавливаем переменные окружения для HuggingFace (если еще не установлены)
        if 'HF_HUB_DOWNLOAD_TIMEOUT' not in os.environ:
            os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '1800'  # 30 минут на загрузку
        if 'HF_HUB_DOWNLOAD_RETRY' not in os.environ:
            os.environ['HF_HUB_DOWNLOAD_RETRY'] = '3'  # 3 попытки
        
        # Загружаем модель с явными параметрами
        logger.info("Вызываем SentenceTransformer для загрузки модели...")
        logger.info("Это может занять 5-15 минут при первом запуске (модель ~500MB)")
        
        try:
            _model_st = SentenceTransformer(
                MODEL_NAME,
                device=device,
                trust_remote_code=False,
                cache_folder=str(cache_dir.parent),
            )
            logger.info("SentenceTransformer инициализирован успешно")
        except Exception as load_error:
            logger.error(f"Ошибка при загрузке модели: {load_error}")
            logger.info("Попытка очистить кэш и загрузить заново...")
            
            # Очищаем кэш и пробуем снова
            try:
                import shutil
                model_cache = cache_dir / f"models--{MODEL_NAME.replace('/', '--')}"
                if model_cache.exists():
                    logger.info(f"Удаляем кэш модели: {model_cache}")
                    shutil.rmtree(model_cache)
            except Exception as cache_error:
                logger.warning(f"Не удалось очистить кэш: {cache_error}")
            
            # Пробуем загрузить снова
            logger.info("Повторная попытка загрузки модели...")
            _model_st = SentenceTransformer(
                MODEL_NAME,
                device=device,
                trust_remote_code=False,
                cache_folder=str(cache_dir.parent),
            )
        
        logger.info(f"✓ Модель '{MODEL_NAME}' успешно загружена на {device}")
        logger.info(f"Размер модели в памяти: ~{_model_st.get_sentence_embedding_dimension()} измерений")
        return _model_st
        
    except Exception as e:
        logger.error(f"✗ Ошибка загрузки модели: {e}", exc_info=True)
        _model_st = None
        raise RuntimeError(f"Не удалось загрузить модель: {e}")


def is_model_loaded() -> bool:
    """Проверяет, загружена ли модель."""
    return _model_st is not None


def _get_model() -> SentenceTransformer:
    """
    Получает загруженную модель.
    
    Returns:
        Загруженная модель
        
    Raises:
        RuntimeError: Если модель не загружена
    """
    if _model_st is None:
        raise RuntimeError(
            "Модель не загружена. Убедитесь, что load_model() была вызвана при старте приложения."
        )
    return _model_st


def make_embedding_from_answer(answer: str) -> np.ndarray:
    """
    Создает эмбеддинг из текста ответа.
    
    Args:
        answer: Текст ответа пользователя
        
    Returns:
        Нормализованный вектор эмбеддинга
        
    Raises:
        ValueError: Если текст пустой
        RuntimeError: Если модель не загружена
    """
    if not answer or not answer.strip():
        raise ValueError("Ответ не может быть пустым")
    
    # Нормализуем текст
    normalized_answer = normalize_text(answer)
    
    # Получаем модель
    model = _get_model()
    
    # Создаем эмбеддинг
    emb = model.encode(
        normalized_answer,
        device=device,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=1,
    )
    
    return emb
