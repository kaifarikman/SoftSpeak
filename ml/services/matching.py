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
    best_id: Optional[int] = None
    best_similarity: float = -1.0

    for candidate in other_users:
        cid = candidate.get("id")
        cvector = candidate.get("profile_vector")
        if cid is None or cvector is None or cid == user_id:
            continue
        distance = cosine_distance(user_vector, cvector)
        similarity = 1.0 - distance
        logger.debug(f"Кандидат {cid}: similarity={similarity:.4f}")
        if similarity >= threshold and similarity > best_similarity:
            best_similarity = similarity
            best_id = cid

    if best_id is not None:
        logger.info(f"Лучший матч: user_id={best_id}, similarity={best_similarity:.4f}")
    else:
        logger.info(f"Матч не найден (threshold={threshold}, кандидатов={len(other_users)})")

    return best_id

