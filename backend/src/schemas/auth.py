from pydantic import BaseModel, EmailStr, SecretStr, Field


class LoginRequest(BaseModel):
    """Запрос на вход по username и password."""

    username: str
    password: SecretStr


class LoginResponse(BaseModel):
    """Ответ после успешной аутентификации."""

    username: str
    message: str = "Authenticated"
    chat_data: dict | None = None  # Данные чата будут добавлены в эндпоинте


class EmailVerificationRequest(BaseModel):
    """Запрос на отправку кода подтверждения на email."""

    username: str
    email: EmailStr
    password: SecretStr = Field(..., min_length=8)


class EmailVerificationResponse(BaseModel):
    """Ответ после создания/отправки кода подтверждения."""

    message: str


class EmailVerificationConfirmRequest(BaseModel):
    """Запрос на подтверждение email кодом из письма."""

    username: str
    code: str


class EmailVerificationConfirmResponse(BaseModel):
    """Ответ после успешного подтверждения email."""

    message: str
    chat_data: dict | None = None  # Данные чата будут добавлены в эндпоинте
