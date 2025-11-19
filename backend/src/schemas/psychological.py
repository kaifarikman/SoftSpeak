"""Схемы для работы с психологическим профилем."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CategorySchema(BaseModel):
    """Схема категории."""

    id: int
    name: str
    description: Optional[str] = None
    order: int

    class Config:
        from_attributes = True


class QuestionSchema(BaseModel):
    """Схема вопроса."""

    id: int
    category_id: int
    text: str
    order: int
    is_active: bool

    class Config:
        from_attributes = True


class QuestionWithCategorySchema(QuestionSchema):
    """Схема вопроса с категорией."""

    category: CategorySchema

    class Config:
        from_attributes = True


class UserAnswerSchema(BaseModel):
    """Схема ответа пользователя."""

    id: int
    user_id: int
    question_id: int
    answer_text: str
    created_at: datetime

    class Config:
        from_attributes = True


class AnswerRequest(BaseModel):
    """Запрос на сохранение ответа."""

    question_id: int
    answer_text: str


class NextQuestionResponse(BaseModel):
    """Ответ с следующим вопросом."""

    question: Optional[QuestionWithCategorySchema] = None
    current_question_number: int
    total_questions: int
    is_completed: bool = False


class PsychologicalProfileSchema(BaseModel):
    """Схема психологического профиля."""

    id: int
    user_id: int
    profile_vector: list[float]  # Вектор психологического профиля
    completed_at: datetime

    class Config:
        from_attributes = True

