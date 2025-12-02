from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):

    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/app"

    jwt_secret: str = Field(
        ...,
        min_length=32,
        description="Секретный ключ для JWT токенов. Должен быть минимум 32 символа. ОБЯЗАТЕЛЬНО измените в продакшене!"
    )
    jwt_access_ttl_min: int = 30
    
    @field_validator('jwt_secret')
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                f"JWT_SECRET должен быть минимум 32 символа. "
                f"Текущая длина: {len(v)}. "
                f"Это критично для безопасности!"
            )
        unsafe_values = [
            "change_me",
            "change-me-in-production-please-use-secure-key",
            "secret",
            "password",
            "default",
            "test",
            "demo"
        ]
        v_lower = v.lower().strip()
        
        if v_lower in [uv.lower() for uv in unsafe_values]:
            raise ValueError(
                f"JWT_SECRET не может быть небезопасным значением. "
                "ОБЯЗАТЕЛЬНО установите уникальный секретный ключ!"
            )
        
        return v

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

    admin_username: str = "admin"
    admin_password: str = "admin"
    admin_token: str = "admin_token_secret_change_in_production"
    
    cors_origins: str = Field(
        default="*",
        description="Разрешенные CORS origins (через запятую). По умолчанию '*' для разработки. В продакшене укажите конкретные домены."
    )

    model_config = SettingsConfigDict(
       env_file=BASE_DIR / ".env",
       env_file_encoding="utf-8",
       case_sensitive=False,
   )

settings = Settings()
