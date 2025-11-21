"""Конфигурация приложения через переменные окружения."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # путь до корня проекта

class Settings(BaseSettings):
    """Настройки приложения из переменных окружения."""

    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/app"

    jwt_secret: str = "change_me"
    jwt_access_ttl_min: int = 30

    email_from: str = "noreply@example.com"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False

    app_base_url: str = "http://localhost:8000"

    verification_code_ttl_min: int = 10
    verification_code_length: int = 6

    rate_limit_email_per_hour: int = 5

    match_similarity_threshold: float = 0.65

    model_config = SettingsConfigDict(
       env_file=BASE_DIR / ".env",
       env_file_encoding="utf-8",
       case_sensitive=False,
   )

settings = Settings()
