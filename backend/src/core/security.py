"""Простые утилиты для хеширования и проверки паролей.

Важно: это только для демо. Для продакшена стоит использовать более надежные
алгоритмы (bcrypt, argon2 и т.д.).
"""
from hashlib import sha256
from secrets import compare_digest


def hash_password(raw_password: str) -> str:
    """Возвращает SHA256-хеш от переданного пароля."""

    return sha256(raw_password.encode("utf-8")).hexdigest()


def verify_password(raw_password: str, hashed_password: str) -> bool:
    """Сравнивает пароль из запроса и хеш, сохраненный у пользователя."""

    return compare_digest(hash_password(raw_password), hashed_password)

