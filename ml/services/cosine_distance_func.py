import numpy as np
from typing import List, Union


def cosine_distance(
    a: Union[np.ndarray, List[float]], 
    b: Union[np.ndarray, List[float]], 
    assume_normalized: bool = False, 
    eps: float = 1e-8
) -> np.ndarray:



