"""Утилиты для хеширования и проверки паролей с использованием bcrypt."""
import bcrypt


def hash_password(raw_password: str) -> str:
    """Возвращает bcrypt-хеш от переданного пароля.
    
    Args:
        raw_password: Пароль в открытом виде
        
    Returns:
        Хеш пароля в формате bcrypt (строка)
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(raw_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(raw_password: str, hashed_password: str) -> bool:
    """Сравнивает пароль из запроса и хеш, сохраненный у пользователя.
    
    Args:
        raw_password: Пароль в открытом виде
        hashed_password: Хеш пароля из базы данных
        
    Returns:
        True если пароль совпадает, False в противном случае
    """
    try:
        return bcrypt.checkpw(
            raw_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        # Обработка старых паролей в формате SHA256 (для миграции)
        # Если хеш не в формате bcrypt, возвращаем False
        return False

