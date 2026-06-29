"""Seed psychological survey categories and questions

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_DATA = [
    {
        "category_name": "Самоопределение",
        "category_description": "Вопросы о том, как вы видите себя и свои сильные стороны.",
        "category_order": 1,
        "question_text": "Что в себе вы считаете самой сильной стороной?",
        "question_order": 1,
    },
    {
        "category_name": "Настроение",
        "category_description": "Как вы переживаете эмоциональные состояния и восстанавливаетесь.",
        "category_order": 2,
        "question_text": "Что обычно помогает вам быстро восстановить настроение?",
        "question_order": 1,
    },
    {
        "category_name": "Общение",
        "category_description": "Про стиль общения и отношения с людьми.",
        "category_order": 3,
        "question_text": "С кем вам легче всего находить общий язык и почему?",
        "question_order": 1,
    },
    {
        "category_name": "Стресс",
        "category_description": "Про реакции на нагрузку и способы справляться со стрессом.",
        "category_order": 4,
        "question_text": "Как вы обычно понимаете, что устали от перегрузки?",
        "question_order": 1,
    },
    {
        "category_name": "Ценности",
        "category_description": "О том, что для вас действительно важно.",
        "category_order": 5,
        "question_text": "Какая ценность для вас сейчас особенно важна в жизни?",
        "question_order": 1,
    },
    {
        "category_name": "Отношения",
        "category_description": "Про близость, доверие и границы.",
        "category_order": 6,
        "question_text": "Что для вас является признаком доверительных отношений?",
        "question_order": 1,
    },
    {
        "category_name": "Работа и учеба",
        "category_description": "О привычках, мотивации и рабочем ритме.",
        "category_order": 7,
        "question_text": "Что помогает вам не терять мотивацию в длинных проектах?",
        "question_order": 1,
    },
    {
        "category_name": "Отдых",
        "category_description": "Про восстановление и свободное время.",
        "category_order": 8,
        "question_text": "Как выглядит ваш идеальный день отдыха?",
        "question_order": 1,
    },
    {
        "category_name": "Привычки",
        "category_description": "Про повседневные ритуалы и режим.",
        "category_order": 9,
        "question_text": "Какая привычка сильнее всего влияет на ваш день?",
        "question_order": 1,
    },
    {
        "category_name": "Будущее",
        "category_description": "Про планы, ожидания и ориентиры.",
        "category_order": 10,
        "question_text": "Какой результат ближайшего года для вас будет самым значимым?",
        "question_order": 1,
    },
]


def _table(name: str) -> sa.Table:
    metadata = sa.MetaData()
    if name == "categories":
        return sa.Table(
            name,
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(128)),
            sa.Column("description", sa.Text),
            sa.Column("order", sa.Integer),
        )
    return sa.Table(
        name,
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("category_id", sa.Integer),
        sa.Column("text", sa.Text),
        sa.Column("order", sa.Integer),
        sa.Column("is_active", sa.Boolean),
    )


def upgrade() -> None:
    bind = op.get_bind()
    categories = _table("categories")
    questions = _table("questions")

    for row in SEED_DATA:
        category_id = bind.execute(
            sa.select(categories.c.id).where(categories.c.name == row["category_name"])
        ).scalar_one_or_none()
        if category_id is None:
            result = bind.execute(
                sa.insert(categories)
                .values(
                    name=row["category_name"],
                    description=row["category_description"],
                    order=row["category_order"],
                )
                .returning(categories.c.id)
            )
            category_id = result.scalar_one()

        existing_question_id = bind.execute(
            sa.select(questions.c.id).where(
                sa.and_(
                    questions.c.category_id == category_id,
                    questions.c.text == row["question_text"],
                )
            )
        ).scalar_one_or_none()
        if existing_question_id is None:
            bind.execute(
                sa.insert(questions).values(
                    category_id=category_id,
                    text=row["question_text"],
                    order=row["question_order"],
                    is_active=True,
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    categories = _table("categories")
    questions = _table("questions")

    for row in SEED_DATA:
        bind.execute(
            sa.delete(questions).where(questions.c.text == row["question_text"])
        )
        bind.execute(
            sa.delete(categories).where(
                sa.and_(
                    categories.c.name == row["category_name"],
                    sa.not_(
                        sa.exists(
                            sa.select(1).where(questions.c.category_id == categories.c.id)
                        )
                    ),
                )
            )
        )
