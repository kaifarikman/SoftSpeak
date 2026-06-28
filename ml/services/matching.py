from typing import List, Optional, Union
import numpy as np
import logging

from .cosine_distance_func import cosine_distance

logger = logging.getLogger(__name__)
TAG_BONUS = 0.15


def _apply_tag_bonus(
    similarity: float, user_tags: set[int], candidate_tags: set[int]
) -> float:
    if user_tags and candidate_tags and user_tags.intersection(candidate_tags):
        return min(1.0, similarity + TAG_BONUS)
    return similarity


def find_best_match(
    user_vector: Union[np.ndarray, List[float]],
    user_id: int,
    other_users: List[dict],
    threshold: float = 0.65,
    user_tags: Optional[List[int]] = None,
) -> Optional[int]:
    best_id: Optional[int] = None
    best_similarity: float = -1.0
    user_tags_set = set(user_tags or [])

    for candidate in other_users:
        cid = candidate.get("id")
        cvector = candidate.get("profile_vector")
        if cid is None or cvector is None or cid == user_id:
            continue
        distance = cosine_distance(user_vector, cvector)
        similarity = 1.0 - distance
        candidate_tags = set(candidate.get("tag_ids") or [])
        similarity = _apply_tag_bonus(similarity, user_tags_set, candidate_tags)
        logger.debug(f"Кандидат {cid}: similarity={similarity:.4f}")
        if similarity >= threshold and similarity > best_similarity:
            best_similarity = similarity
            best_id = cid

    if best_id is not None:
        logger.info(f"Лучший матч: user_id={best_id}, similarity={best_similarity:.4f}")
    else:
        logger.info(f"Матч не найден (threshold={threshold}, кандидатов={len(other_users)})")

    return best_id
