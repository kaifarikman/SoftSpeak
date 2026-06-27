"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nickname", sa.String(64), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("full_name", sa.String(128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("anonym", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("ai_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("messengers_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("settings_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("notification_anon_chats", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notification_open_chats", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("reports_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_nickname", "users", ["nickname"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "email_verification_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_verification_codes_user_id", "email_verification_codes", ["user_id"])

    op.create_table(
        "chats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chats_user_id", "chats", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_from_user", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_chat_id", "messages", ["chat_id"])

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_questions_category_id", "questions", ["category_id"])

    op.create_table(
        "user_answers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_answers_user_id", "user_answers", ["user_id"])
    op.create_index("ix_user_answers_question_id", "user_answers", ["question_id"])

    op.create_table(
        "psychological_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("profile_vector", postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_psychological_profiles_user_id", "psychological_profiles", ["user_id"])

    # reports создаём до anonymous_chats из-за циклической FK
    # anonymous_chats.blocked_by_report_id → reports.id добавляется через alter_table ниже
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reporter_id", sa.Integer(), nullable=False),
        sa.Column("reported_user_id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=True),  # FK добавим после anonymous_chats
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_admin_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reported_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_reporter_id", "reports", ["reporter_id"])
    op.create_index("ix_reports_reported_user_id", "reports", ["reported_user_id"])
    op.create_index("ix_reports_status", "reports", ["status"])

    op.create_table(
        "anonymous_chats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user1_id", sa.Integer(), nullable=False),
        sa.Column("user2_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("revealed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user1_revealed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("user2_revealed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("user1_alias", sa.String(128), nullable=False, server_default="Собеседник"),
        sa.Column("user2_alias", sa.String(128), nullable=False, server_default="Собеседник"),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("blocked_by_report_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user1_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user2_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blocked_by_report_id"], ["reports.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_anonymous_chats_user1_id", "anonymous_chats", ["user1_id"])
    op.create_index("ix_anonymous_chats_user2_id", "anonymous_chats", ["user2_id"])

    # Теперь добавляем FK от reports.chat_id → anonymous_chats.id
    op.create_foreign_key(
        "fk_reports_chat_id",
        "reports", "anonymous_chats",
        ["chat_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_reports_chat_id", "reports", ["chat_id"])

    op.create_table(
        "anonymous_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["chat_id"], ["anonymous_chats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_anonymous_messages_chat_id", "anonymous_messages", ["chat_id"])
    op.create_index("ix_anonymous_messages_sender_id", "anonymous_messages", ["sender_id"])

    op.create_table(
        "matchmaking_queue",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_searching", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_matchmaking_queue_user_id", "matchmaking_queue", ["user_id"])

    op.create_table(
        "random_name_adjectives",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("text", sa.String(128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("text"),
    )

    op.create_table(
        "random_name_nouns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("text", sa.String(128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("text"),
    )


def downgrade() -> None:
    op.drop_table("random_name_nouns")
    op.drop_table("random_name_adjectives")
    op.drop_table("matchmaking_queue")
    op.drop_index("ix_anonymous_messages_sender_id", table_name="anonymous_messages")
    op.drop_index("ix_anonymous_messages_chat_id", table_name="anonymous_messages")
    op.drop_table("anonymous_messages")
    op.drop_constraint("fk_reports_chat_id", "reports", type_="foreignkey")
    op.drop_index("ix_reports_chat_id", table_name="reports")
    op.drop_index("ix_anonymous_chats_user2_id", table_name="anonymous_chats")
    op.drop_index("ix_anonymous_chats_user1_id", table_name="anonymous_chats")
    op.drop_table("anonymous_chats")
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_index("ix_reports_reported_user_id", table_name="reports")
    op.drop_index("ix_reports_reporter_id", table_name="reports")
    op.drop_table("reports")
    op.drop_index("ix_psychological_profiles_user_id", table_name="psychological_profiles")
    op.drop_table("psychological_profiles")
    op.drop_index("ix_user_answers_question_id", table_name="user_answers")
    op.drop_index("ix_user_answers_user_id", table_name="user_answers")
    op.drop_table("user_answers")
    op.drop_index("ix_questions_category_id", table_name="questions")
    op.drop_table("questions")
    op.drop_table("categories")
    op.drop_index("ix_messages_chat_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_chats_user_id", table_name="chats")
    op.drop_table("chats")
    op.drop_index("ix_email_verification_codes_user_id", table_name="email_verification_codes")
    op.drop_table("email_verification_codes")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_nickname", table_name="users")
    op.drop_table("users")
