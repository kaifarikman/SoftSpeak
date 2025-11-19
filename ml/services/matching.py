"""Поиск лучшего совпадения пользователей по психологическому профилю."""
from typing import List, Optional, Union
import numpy as np

from .cosine_distance_func import cosine_distance


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

    for other_user in other_users:
        if other_user.get('id') == user_id:
            continue
        
        other_vector = other_user.get('profile_vector')
        if other_vector is None:
            continue
            
        other_vector = np.array(other_vector)
        distance = cosine_distance(user_vector, other_vector)
        
        # cosine_distance возвращает массив, берем первое значение
        if isinstance(distance, np.ndarray):
            distance = distance.item() if distance.size == 1 else distance[0, 0]
        
        # Проверяем порог similarity
        # Cosine distance: 0 = идентичны, 2 = противоположны
        # Similarity = 1 - distance/2 (приводим к шкале 0-1)
        similarity = 1 - distance / 2
        
        # Пропускаем пользователей с низкой совместимостью
        if similarity < threshold:
            continue
        
        if distance < min_distance:
            min_distance = distance
            best_match_id = other_user['id']

    return best_match_id

