"""Утилиты для работы с векторами эмбеддингов."""
import numpy as np
from typing import List, Union


def create_profile_vector_from_embeddings(
    embeddings: List[Union[List[float], np.ndarray]]
) -> List[float]:
    """
    Создает финальный вектор профиля из эмбеддингов ответов.
    
    Усредняет все эмбеддинги и нормализует результат.
    Это более эффективно, чем конкатенация (768 измерений вместо 768*N).
    
    Args:
        embeddings: Список эмбеддингов (каждый может быть списком или numpy массивом)
        
    Returns:
        Нормализованный вектор профиля в виде списка float
        
    Raises:
        ValueError: Если список эмбеддингов пуст
    """
    if not embeddings:
        raise ValueError("Список эмбеддингов пуст")
    
    # Преобразуем в numpy массивы
    np_embeddings = [np.array(emb) for emb in embeddings]
    
    # Усредняем все эмбеддинги (mean pooling)
    # Это сохраняет размерность 768 и лучше для similarity search
    averaged = np.mean(np_embeddings, axis=0)
    
    # Нормализуем
    norm = np.linalg.norm(averaged)
    if norm == 0:
        raise ValueError("Норма вектора равна нулю")
    
    vector = averaged / norm
    
    return vector.tolist()

