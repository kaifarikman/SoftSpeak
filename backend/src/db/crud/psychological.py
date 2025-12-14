from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.db.models import Category, Question, UserAnswer, User, PsychologicalProfile


async def get_all_categories(session: AsyncSession) -> list[Category]:
    stmt = select(Category).order_by(Category.order)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_category_by_id(
    session: AsyncSession, category_id: int
) -> Optional[Category]:
    stmt = select(Category).where(Category.id == category_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_questions_by_category(
    session: AsyncSession, category_id: int, only_active: bool = True
) -> list[Question]:
    stmt = select(Question).where(Question.category_id == category_id)
    if only_active:
        stmt = stmt.where(Question.is_active.is_(True))
    stmt = stmt.order_by(Question.order)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_question_by_id(
    session: AsyncSession, question_id: int
) -> Optional[Question]:
    stmt = select(Question).where(Question.id == question_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_next_question_for_user(
    session: AsyncSession, user_id: int
) -> Optional[tuple[Question, int, int]]:
    categories = await get_all_categories(session)
    categories = sorted(categories, key=lambda c: c.order)
    stmt = select(UserAnswer).where(UserAnswer.user_id == user_id)
    result = await session.execute(stmt)
    user_answers = list(result.scalars().all())
    answered_question_ids = {answer.question_id for answer in user_answers}
    total_questions = 10
    for category in categories:
        questions = await get_questions_by_category(
            session, category.id, only_active=True
        )
        if questions:
            question = questions[0]
            if question.id not in answered_question_ids:
                current_number = len(answered_question_ids) + 1
                return (question, current_number, total_questions)
    return None


async def save_user_answer(
    session: AsyncSession,
    user_id: int,
    question_id: int,
    answer_text: str,
    embedding: Optional[list[float]] = None,
) -> UserAnswer:
    answer = UserAnswer(
        user_id=user_id,
        question_id=question_id,
        answer_text=answer_text,
        embedding=embedding,
    )
    session.add(answer)
    await session.commit()
    await session.refresh(answer)
    return answer


async def get_user_answers_count(session: AsyncSession, user_id: int) -> int:
    stmt = select(func.count(UserAnswer.id)).where(UserAnswer.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar() or 0


async def get_user_answers(session: AsyncSession, user_id: int) -> list[UserAnswer]:
    stmt = (
        select(UserAnswer)
        .where(UserAnswer.user_id == user_id)
        .options(selectinload(UserAnswer.question))
        .order_by(UserAnswer.created_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_psychological_profile(
    session: AsyncSession, user_id: int, profile_vector: list[float]
) -> PsychologicalProfile:
    profile = PsychologicalProfile(user_id=user_id, profile_vector=profile_vector)
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile


async def get_psychological_profile(
    session: AsyncSession, user_id: int
) -> Optional[PsychologicalProfile]:
    stmt = select(PsychologicalProfile).where(PsychologicalProfile.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def has_completed_profile(session: AsyncSession, user_id: int) -> bool:
    profile = await get_psychological_profile(session, user_id)
    return profile is not None
