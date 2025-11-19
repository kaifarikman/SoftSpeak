"""API эндпоинты для работы с психологическим профилем."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.db.crud.psychological import (
    get_next_question_for_user,
    save_user_answer,
    get_user_answers_count,
    get_user_answers,
    create_psychological_profile,
    has_completed_profile,
    get_psychological_profile as get_user_psychological_profile_crud,
)
from src.db.crud.auth import get_user_by_username
from src.schemas.psychological import (
    NextQuestionResponse,
    AnswerRequest,
    QuestionWithCategorySchema,
    UserAnswerSchema,
    PsychologicalProfileSchema,
)
from src.services.vector_utils import create_profile_vector, create_embedding

router = APIRouter(prefix="/psychological", tags=["psychological"])


@router.get("/next-question/{username}", response_model=NextQuestionResponse)
async def get_next_question(
    username: str,
    session: AsyncSession = Depends(get_db),
) -> NextQuestionResponse:
    """Получает следующий вопрос для пользователя."""
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    # Проверяем, завершен ли профиль
    if await has_completed_profile(session, user.id):
        return NextQuestionResponse(
            question=None,
            current_question_number=10,
            total_questions=10,
            is_completed=True,
        )
    
    result = await get_next_question_for_user(session, user.id)
    
    if result is None:
        # Все вопросы отвечены, создаем профиль
        answers = await get_user_answers(session, user.id)
        if len(answers) >= 10:
            # Создаем психологический портрет
            embeddings = [answer.embedding for answer in answers if answer.embedding]
            if embeddings:
                profile_vector = await create_profile_vector(embeddings)
                await create_psychological_profile(session, user.id, profile_vector)
                
                # Разблокируем messengers
                user.messengers_enabled = True
                await session.commit()
        
        return NextQuestionResponse(
            question=None,
            current_question_number=10,
            total_questions=10,
            is_completed=True,
        )
    
    question, current_number, total_count = result
    
    # Загружаем категорию
    await session.refresh(question, ["category"])
    
    return NextQuestionResponse(
        question=QuestionWithCategorySchema.model_validate(question),
        current_question_number=current_number,
        total_questions=total_count,
        is_completed=False,
    )


@router.post("/answer/{username}", response_model=UserAnswerSchema)
async def submit_answer(
    username: str,
    request: AnswerRequest,
    session: AsyncSession = Depends(get_db),
) -> UserAnswerSchema:
    """Сохраняет ответ пользователя на вопрос."""
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    # Проверяем, не завершен ли уже профиль
    if await has_completed_profile(session, user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Профиль уже завершен",
        )
    
    # Создаем вектор для ответа
    embedding_list = await create_embedding(request.answer_text)
    
    # Сохраняем ответ
    answer = await save_user_answer(
        session,
        user.id,
        request.question_id,
        request.answer_text,
        embedding_list,
    )
    
    # Проверяем, все ли вопросы отвечены
    answers_count = await get_user_answers_count(session, user.id)
    if answers_count >= 10:
        # Создаем психологический портрет
        answers = await get_user_answers(session, user.id)
        embeddings = [answer.embedding for answer in answers if answer.embedding]
        if embeddings:
            profile_vector = await create_profile_vector(embeddings)
            await create_psychological_profile(session, user.id, profile_vector)
            
            # Разблокируем messengers
            user.messengers_enabled = True
            await session.commit()
    
    return UserAnswerSchema.model_validate(answer)


@router.get("/status/{username}")
async def get_profile_status(
    username: str,
    session: AsyncSession = Depends(get_db),
):
    """Получает статус создания профиля."""
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    answers_count = await get_user_answers_count(session, user.id)
    is_completed = await has_completed_profile(session, user.id)
    
    return {
        "answers_count": answers_count,
        "is_completed": is_completed,
        "messengers_enabled": user.messengers_enabled,
    }


@router.get("/profile/{username}", response_model=PsychologicalProfileSchema)
async def get_psychological_profile(
    username: str,
    session: AsyncSession = Depends(get_db),
) -> PsychologicalProfileSchema:
    """Получает психологический профиль пользователя (вектор)."""
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    profile = await get_user_psychological_profile_crud(session, user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Психологический профиль не найден. Пройдите опрос.",
        )
    
    return PsychologicalProfileSchema.model_validate(profile)


@router.get("/profile/{username}/vector")
async def get_profile_vector(
    username: str,
    session: AsyncSession = Depends(get_db),
):
    """Получает только вектор профиля пользователя (для удобства просмотра)."""
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    profile = await get_user_psychological_profile_crud(session, user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Психологический профиль не найден. Пройдите опрос.",
        )
    
    return {
        "username": username,
        "user_id": user.id,
        "vector_length": len(profile.profile_vector),
        "vector": profile.profile_vector,
        "completed_at": profile.completed_at.isoformat(),
    }

