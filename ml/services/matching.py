"""Поиск лучшего совпадения пользователей по психологическому профилю."""
from typing import List, Optional, Union
import numpy as np
import logging

from .cosine_distance_func import cosine_distance

logger = logging.getLogger(__name__)


def find_best_match(
    user_vector: Union[np.ndarray, List[float]],
    user_id: int,
    other_users: List[dict],
    threshold: float = 0.65,
) -> Optional[int]:
    """
    Находит пользователя с наиболее похожим психологическим профилем.
    
    Args:
        user_vector: Вектор психологического профиля текущего пользователя
        user_id: ID текущего пользователя (чтобы исключить его из поиска)
        other_users: Список словарей с ключами 'id' и 'profile_vector'
        threshold: Минимальный порог similarity (0-1), по умолчанию 0.65
        
    Returns:
        ID пользователя с лучшим совпадением или None, если нет подходящих кандидатов
        
    Note:
        Cosine distance: 0 = идентичные векторы, 2 = противоположные
        Similarity = 1 - distance/2, где similarity ∈ [0, 1]
    """
    if not other_users:
        return None
    
    user_vector = np.array(user_vector, dtype=np.float32)
    
    # Нормализуем вектор пользователя один раз перед циклом
    user_norm = np.linalg.norm(user_vector)
    if user_norm > 0:
        user_vector = user_vector / user_norm
    else:
        logger.error(f"Вектор пользователя {user_id} имеет нулевую норму")
        return None
    
    all_candidates = []  # Собираем всех кандидатов с их similarity
    
    for other_user in other_users:
        if other_user.get('id') == user_id:
            continue
        
        other_vector = other_user.get('profile_vector')
        if other_vector is None:
            continue
            
        other_vector = np.array(other_vector, dtype=np.float32)
        
        # Нормализуем вектор другого пользователя
        other_norm = np.linalg.norm(other_vector)
        if other_norm == 0:
            logger.warning(f"Вектор пользователя {other_user.get('id')} имеет нулевую норму, пропускаем")
            continue
        other_vector = other_vector / other_norm
        
        # Вычисляем cosine similarity напрямую (dot product для нормализованных векторов)
        cosine_similarity = float(np.dot(user_vector, other_vector))
        
        # Cosine similarity для нормализованных эмбеддингов обычно от 0 до 1
        # Используем его напрямую как similarity
        similarity = max(0.0, cosine_similarity)  # Ограничиваем снизу нулем
        
        # Также вычисляем distance для логирования
        distance = 1.0 - cosine_similarity
        
        # Сохраняем всех кандидатов с их метриками
        all_candidates.append({
            'id': other_user['id'],
            'distance': distance,
            'similarity': similarity
        })
    
    if not all_candidates:
        return None
    
    # Сортируем всех кандидатов по similarity (от большего к меньшему)
    all_candidates.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Логируем всех кандидатов для отладки
    logger.info(f"Всего кандидатов для сравнения: {len(all_candidates)}")
    logger.info(f"Топ-5 кандидатов (по similarity):")
    for i, cand in enumerate(all_candidates[:5], 1):
        logger.info(
            f"  {i}. Пользователь {cand['id']}: similarity={cand['similarity']:.4f}, "
            f"distance={cand['distance']:.4f}"
        )
    
    # Выбираем лучшего кандидата, который проходит порог
    for candidate in all_candidates:
        if candidate['similarity'] >= threshold:
            logger.info(
                f"✓ Найден лучший матч: пользователь {candidate['id']} "
                f"(similarity: {candidate['similarity']:.4f}, distance: {candidate['distance']:.4f}, "
                f"порог: {threshold:.4f})"
            )
            return candidate['id']
    
    # Если никто не прошел порог, возвращаем лучшего кандидата все равно
    # (но с предупреждением в логах)
    best_candidate = all_candidates[0]
    logger.warning(
        f"⚠ Нет кандидатов, прошедших порог {threshold:.4f}. "
        f"Возвращаем лучшего доступного: пользователь {best_candidate['id']} "
        f"(similarity: {best_candidate['similarity']:.4f}, distance: {best_candidate['distance']:.4f})"
    )
    return best_candidate['id']

