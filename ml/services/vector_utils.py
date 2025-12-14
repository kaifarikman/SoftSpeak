import numpy as np
from typing import List, Union


def create_profile_vector_from_embeddings(
    embeddings: List[Union[List[float], np.ndarray]],
) -> List[float]:
    if not embeddings:
        raise ValueError("Список эмбеддингов пуст")

    EXPECTED_DIM = 768

    np_embeddings = []
    for i, emb in enumerate(embeddings):
        emb_array = np.array(emb)
        if len(emb_array) != EXPECTED_DIM:
            raise ValueError(
                f"Неверная размерность эмбеддинга #{i}: ожидалось {EXPECTED_DIM}, "
                f"получено {len(emb_array)}"
            )
        np_embeddings.append(emb_array)

    averaged = np.mean(np_embeddings, axis=0)
    norm = np.linalg.norm(averaged)
    if norm == 0:
        raise ValueError("Норма вектора равна нулю")

    vector = averaged / norm

    return vector.tolist()
