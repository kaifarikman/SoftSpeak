"""ORM-модели приложения."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, ARRAY, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

class User(Base):
    """Пользователь системы."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    avatar: Mapped[str | None] = mapped_column(String(512), nullable=True, default="")
    anonym: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    messengers_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    settings_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Настройки профиля
    bio: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)  # Информация о себе
    
    # Настройки уведомлений
    notification_anon_chats: Mapped[bool] = mapped_column(Boolean, default=True)  # Уведомления из анонимных чатов
    notification_open_chats: Mapped[bool] = mapped_column(Boolean, default=True)  # Уведомления из открытых чатов
    
    # Настройки медиа
    media_auto_upload_photos: Mapped[bool] = mapped_column(Boolean, default=False)  # Автозагрузка фото
    media_auto_upload_videos: Mapped[bool] = mapped_column(Boolean, default=False)  # Автозагрузка видео
    verification_codes: Mapped[list["EmailVerificationCode"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    ai_chats: Mapped[list["Chat"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    answers: Mapped[list["UserAnswer"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    psychological_profile: Mapped["PsychologicalProfile | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    anonymous_chats_as_user1: Mapped[list["AnonymousChat"]] = relationship(
        "AnonymousChat",
        foreign_keys="AnonymousChat.user1_id",
        back_populates="user1",
        cascade="all, delete-orphan",
    )
    anonymous_chats_as_user2: Mapped[list["AnonymousChat"]] = relationship(
        "AnonymousChat",
        foreign_keys="AnonymousChat.user2_id",
        back_populates="user2",
        cascade="all, delete-orphan",
    )
    matchmaking_queue: Mapped["MatchmakingQueue | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    blocked_users: Mapped[list["Blacklist"]] = relationship(
        "Blacklist",
        foreign_keys="Blacklist.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    blocked_by_users: Mapped[list["Blacklist"]] = relationship(
        "Blacklist",
        foreign_keys="Blacklist.blocked_user_id",
        back_populates="blocked_user",
        cascade="all, delete-orphan",
    )


class EmailVerificationCode(Base):
    """Коды подтверждения email для активации учетных записей."""

    __tablename__ = "email_verification_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="verification_codes")


class Chat(Base):
    """Чат пользователя с AI."""

    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="ai_chats")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    """Сообщение в чате."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_from_user: Mapped[bool] = mapped_column(Boolean, default=True)  # True - от пользователя, False - от AI
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    chat: Mapped["Chat"] = relationship(back_populates="messages")


class Category(Base):
    """Категория вопросов для психологического портрета."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # Порядок отображения

    questions: Mapped[list["Question"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="Question.order",
    )


class Question(Base):
    """Вопрос для категории."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # Порядок в категории
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    category: Mapped["Category"] = relationship(back_populates="questions")
    answers: Mapped[list["UserAnswer"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
    )


class UserAnswer(Base):
    """Ответ пользователя на вопрос."""

    __tablename__ = "user_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"),
        index=True,
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(ARRAY(Float), nullable=True)  # Эмбеддинг ответа
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship(back_populates="answers")


class PsychologicalProfile(Base):
    """Психологический портрет пользователя (финальный вектор)."""

    __tablename__ = "psychological_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        unique=True,
    )
    profile_vector: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)  # Финальный вектор
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="psychological_profile")


class AnonymousChat(Base):
    """Анонимный чат между двумя пользователями."""

    __tablename__ = "anonymous_chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user1_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    user2_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    revealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user1_revealed: Mapped[bool] = mapped_column(Boolean, default=False)  # user1 хочет раскрыться
    user2_revealed: Mapped[bool] = mapped_column(Boolean, default=False)  # user2 хочет раскрыться
    user1_alias: Mapped[str] = mapped_column(String(128), nullable=False, default="Собеседник")
    user2_alias: Mapped[str] = mapped_column(String(128), nullable=False, default="Собеседник")

    user1: Mapped["User"] = relationship("User", foreign_keys=[user1_id], back_populates="anonymous_chats_as_user1")
    user2: Mapped["User"] = relationship("User", foreign_keys=[user2_id], back_populates="anonymous_chats_as_user2")
    messages: Mapped[list["AnonymousMessage"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="AnonymousMessage.created_at",
    )


class AnonymousMessage(Base):
    """Сообщение в анонимном чате."""

    __tablename__ = "anonymous_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("anonymous_chats.id", ondelete="CASCADE"),
        index=True,
    )
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    media_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    media_preview_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    media_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    media_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    media_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    media_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    chat: Mapped["AnonymousChat"] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship("User")


class MatchmakingQueue(Base):
    """Очередь пользователей, ищущих матч."""

    __tablename__ = "matchmaking_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        unique=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    is_searching: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="matchmaking_queue")


class Blacklist(Base):
    """Черный список пользователей."""

    __tablename__ = "blacklist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    blocked_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="blocked_users")
    blocked_user: Mapped["User"] = relationship("User", foreign_keys=[blocked_user_id], back_populates="blocked_by_users")

    # Уникальный индекс: один пользователь не может заблокировать другого дважды
    __table_args__ = (
        UniqueConstraint('user_id', 'blocked_user_id', name='uq_blacklist_user_blocked'),
    )


class RandomNameAdjective(Base):
    """Список прилагательных для генерации псевдонимов."""

    __tablename__ = "random_name_adjectives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class RandomNameNoun(Base):
    """Список существительных для генерации псевдонимов."""

    __tablename__ = "random_name_nouns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
