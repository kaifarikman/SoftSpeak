import numpy as np
from typing import List, Union


def cosine_distance(
    a: Union[np.ndarray, List[float]],
    b: Union[np.ndarray, List[float]],
    assume_normalized: bool = False,
    eps: float = 1e-8,
) -> float:
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    if assume_normalized:
        return float(1.0 - np.dot(a, b))
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < eps or norm_b < eps:
        return 1.0
    return float(1.0 - np.dot(a, b) / (norm_a * norm_b))
