from pydantic import BaseModel, EmailStr, SecretStr, Field, field_validator
from src.core.config import settings


def get_allowed_email_domains() -> set[str]:
    return {
        domain.strip().lower()
        for domain in settings.allowed_email_domains.split(",")
        if domain.strip()
    }


def validate_email_domain(email: str) -> str:
    domain = email.lower().split("@")[-1]
    allowed_domains = get_allowed_email_domains()
    if domain not in allowed_domains:
        raise ValueError("Доступные ящики: mail.ru, yandex.ru, gmail.com")
    return email


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr

    @field_validator("email")
    @classmethod
    def check_email_domain(cls, v: str) -> str:
        return validate_email_domain(v)


class LoginResponse(BaseModel):
    nickname: str
    email: EmailStr
    access_token: str
    token_type: str = "bearer"
    message: str = "Authenticated"
    chat_data: dict | None = None


class EmailVerificationRequest(BaseModel):
    nickname: str = Field(..., min_length=3, max_length=15)
    email: EmailStr
    password: SecretStr = Field(..., min_length=8)

    @field_validator("email")
    @classmethod
    def check_email_domain(cls, v: str) -> str:
        return validate_email_domain(v)


class EmailVerificationResponse(BaseModel):
    message: str


class EmailVerificationConfirmRequest(BaseModel):
    nickname: str
    code: str


class EmailVerificationConfirmResponse(BaseModel):
    message: str
    chat_data: dict | None = None


class AuthMeResponse(BaseModel):
    nickname: str
    email: EmailStr
    chat_data: dict
    is_banned: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
