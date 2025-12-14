from pydantic import BaseModel, EmailStr, SecretStr, Field, field_validator

ALLOWED_EMAIL_DOMAINS = {
    "yandex.ru",
    "yandex.com",
    "ya.ru",
    "mail.ru",
    "inbox.ru",
    "list.ru",
    "bk.ru",
    "gmail.com",
}


def validate_email_domain(email: str) -> str:
    domain = email.lower().split("@")[-1]
    if domain not in ALLOWED_EMAIL_DOMAINS:
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
