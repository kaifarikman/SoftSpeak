"""Схемы для админки."""
from pydantic import BaseModel


class AdminLoginRequest(BaseModel):
    """Запрос на вход в админку."""

    username: str
    password: str


class AdminLoginResponse(BaseModel):
    """Ответ после входа в админку."""

    message: str
    token: str  # Простой токен для админки


class QuestionCreateRequest(BaseModel):
    """Запрос на создание вопроса."""

    category_id: int
    text: str
    order: int = 0
    is_active: bool = True


class QuestionUpdateRequest(BaseModel):
    """Запрос на обновление вопроса."""

    text: str | None = None
    order: int | None = None
    is_active: bool | None = None


class CategoryCreateRequest(BaseModel):
    """Запрос на создание категории."""

    name: str
    description: str | None = None
    order: int = 0


class RandomWordSchema(BaseModel):
    """Схема случайного слова (прилагательное/существительное)."""

    id: int
    text: str
    is_active: bool

    class Config:
        from_attributes = True


class RandomWordCreateRequest(BaseModel):
    """Создание нового слова."""

    text: str


class RandomWordUpdateRequest(BaseModel):
    """Обновление слова."""

    text: str | None = None
    is_active: bool | None = None

