"""Простая авторизация для админки."""
from datetime import datetime, timedelta, timezone

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"
ADMIN_TOKEN = "admin_token_secret_change_in_production"  # В продакшене использовать JWT


def verify_admin(username: str, password: str) -> bool:
    """Проверяет учетные данные админа."""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD


def verify_admin_token(token: str) -> bool:
    """Проверяет токен админа."""
    return token == ADMIN_TOKEN

