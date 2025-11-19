"""Функции для вычисления косинусного расстояния между векторами."""
import numpy as np
from typing import List, Union


def cosine_distance(
    a: Union[np.ndarray, List[float]], 
    b: Union[np.ndarray, List[float]], 
    assume_normalized: bool = False, 
    eps: float = 1e-8
) -> np.ndarray:
    """
    Косинусное расстояние между векторами/наборами векторов.
    a: shape (d,) или (N, d)
    b: shape (d,) или (M, d)
    assume_normalized: если True, предполагается L2-нормировка входов (ускоряет расчёт)
    return: матрица расстояний shape (N, M); если оба входа 1D -> shape (1,1)
    """
    a = np.asarray(a)
    b = np.asarray(b)
    if a.ndim == 1:
        a = a[None, :]
    if b.ndim == 1:
        b = b[None, :]

    if not assume_normalized:
        a = a / (np.linalg.norm(a, axis=-1, keepdims=True) + eps)
        b = b / (np.linalg.norm(b, axis=-1, keepdims=True) + eps)

    sim = a @ b.T  # cosine similarity при L2-нормировке
    return 1.0 - sim

