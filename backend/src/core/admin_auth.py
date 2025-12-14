import logging
from src.core.config import settings

logger = logging.getLogger(__name__)


def verify_admin(username: str, password: str) -> bool:
    expected_username = settings.admin_username
    expected_password = settings.admin_password
    result = username == expected_username and password == expected_password
    logger.info(
        f"Admin login attempt: username='{username}' (expected='{expected_username}'), password match={password == expected_password}, result={result}"
    )
    return result


def verify_admin_token(token: str) -> bool:
    return token == settings.admin_token


def get_admin_token() -> str:
    return settings.admin_token
