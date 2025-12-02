from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CategorySchema(BaseModel):

    id: int
    name: str
    description: Optional[str] = None
    order: int

    class Config:
        from_attributes = True


class QuestionSchema(BaseModel):

    id: int
    category_id: int
    text: str
    order: int
    is_active: bool

    class Config:
        from_attributes = True


class QuestionWithCategorySchema(QuestionSchema):

    category: CategorySchema

    class Config:
        from_attributes = True


class UserAnswerSchema(BaseModel):

    id: int
    user_id: int
    question_id: int
    answer_text: str
    created_at: datetime

    class Config:
        from_attributes = True


class AnswerRequest(BaseModel):

    question_id: int
    answer_text: str


class NextQuestionResponse(BaseModel):

    question: Optional[QuestionWithCategorySchema] = None
    current_question_number: int
    total_questions: int
    is_completed: bool = False


class PsychologicalProfileSchema(BaseModel):

    id: int
    user_id: int
    profile_vector: list[float]
    completed_at: datetime

    class Config:
        from_attributes = True

