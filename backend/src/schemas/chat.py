"""Схемы для работы с чатами и сообщениями."""
from datetime import datetime
from typing import Literal, Union

from pydantic import BaseModel, Field


class MessageSchema(BaseModel):
    """Схема сообщения."""

    id: int
    content: str
    is_from_user: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    """Ответ с данными чата для фронтенда."""

    ai: Union[Literal[True], Literal[False], Literal["start_survey"], list[MessageSchema]] = Field(
        ...,
        description=(
            "True если новый чат, False если AI недоступен, "
            "'start_survey' если нужно начать опрос, "
            "или массив сообщений если чат существует"
        )
    )
    anonym: bool = Field(..., description="Флаг анонимности пользователя")
    messengers: bool = Field(..., description="Доступность вкладки мессенджеров")
    settings: bool = Field(..., description="Доступность настроек")
    avatar: str = Field(default="", description="URL аватара пользователя")
    media_auto_upload_photos: bool = Field(default=False)
    media_auto_upload_videos: bool = Field(default=False)

    class Config:
        from_attributes = True

