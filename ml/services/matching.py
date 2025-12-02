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
    
    user_vector = np.array(user_vector)
    min_distance = float('inf')
    best_match_id = None
    best_similarity = -1
    candidates_passed = []
    
    for other_user in other_users:
        if other_user.get('id') == user_id:
            continue
        
        other_vector = other_user.get('profile_vector')
        if other_vector is None:
            continue
            
        other_vector = np.array(other_vector)
        distance = cosine_distance(user_vector, other_vector)
        
        if isinstance(distance, np.ndarray):
            distance = distance.item() if distance.size == 1 else distance[0, 0]
        
        similarity = 1 - distance / 2
        
        if similarity < threshold:
            continue
        
        candidates_passed.append({
            'id': other_user['id'],
            'distance': distance,
            'similarity': similarity
        })
        
        if distance < min_distance:
            min_distance = distance
            best_similarity = similarity
            best_match_id = other_user['id']
    
    if best_match_id:
        logger.info(f"Найден лучший матч: пользователь {best_match_id} (similarity: {best_similarity:.3f}, distance: {min_distance:.3f})")
        if len(candidates_passed) > 1:
            logger.info(f"Всего кандидатов, прошедших порог {threshold}: {len(candidates_passed)}")
            for cand in sorted(candidates_passed, key=lambda x: x['distance'])[:3]:
                logger.info(f"  - Пользователь {cand['id']}: similarity={cand['similarity']:.3f}, distance={cand['distance']:.3f}")

    return best_match_id

