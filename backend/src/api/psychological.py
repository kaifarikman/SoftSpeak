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
from src.db.crud.auth import get_user_by_email
from src.schemas.psychological import (
    NextQuestionResponse,
    AnswerRequest,
    QuestionWithCategorySchema,
    UserAnswerSchema,
    PsychologicalProfileSchema,
)
from src.services.vector_utils import create_profile_vector, create_embedding

router = APIRouter(prefix="/psychological", tags=["psychological"])


@router.get("/next-question/{email}", response_model=NextQuestionResponse)
async def get_next_question(
    email: str,
    session: AsyncSession = Depends(get_db),
) -> NextQuestionResponse:
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    if await has_completed_profile(session, user.id):
        return NextQuestionResponse(
            question=None,
            current_question_number=10,
            total_questions=10,
            is_completed=True,
        )
    
    result = await get_next_question_for_user(session, user.id)
    
    if result is None:
        answers = await get_user_answers(session, user.id)
        if len(answers) >= 10:
            embeddings = [answer.embedding for answer in answers if answer.embedding]
            if embeddings:
                profile_vector = await create_profile_vector(embeddings)
                await create_psychological_profile(session, user.id, profile_vector)
                
                user.messengers_enabled = True
                await session.commit()
        
        return NextQuestionResponse(
            question=None,
            current_question_number=10,
            total_questions=10,
            is_completed=True,
        )
    
    question, current_number, total_count = result
    
    await session.refresh(question, ["category"])
    
    return NextQuestionResponse(
        question=QuestionWithCategorySchema.model_validate(question),
        current_question_number=current_number,
        total_questions=total_count,
        is_completed=False,
    )


@router.post("/answer/{email}", response_model=UserAnswerSchema)
async def submit_answer(
    email: str,
    request: AnswerRequest,
    session: AsyncSession = Depends(get_db),
) -> UserAnswerSchema:
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    if await has_completed_profile(session, user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Профиль уже завершен",
        )
    
    embedding_list = await create_embedding(request.answer_text)
    
    answer = await save_user_answer(
        session,
        user.id,
        request.question_id,
        request.answer_text,
        embedding_list,
    )
    
    answers_count = await get_user_answers_count(session, user.id)
    if answers_count >= 10:
        answers = await get_user_answers(session, user.id)
        embeddings = [answer.embedding for answer in answers if answer.embedding]
        if embeddings:
            profile_vector = await create_profile_vector(embeddings)
            await create_psychological_profile(session, user.id, profile_vector)
            
            user.messengers_enabled = True
            user.ai_enabled = False  # Отключаем AI чат после завершения опроса
            await session.commit()
    
    return UserAnswerSchema.model_validate(answer)


@router.get("/status/{email}")
async def get_profile_status(
    email: str,
    session: AsyncSession = Depends(get_db),
):
    user = await get_user_by_email(session, email)
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


@router.get("/profile/{email}", response_model=PsychologicalProfileSchema)
async def get_psychological_profile(
    email: str,
    session: AsyncSession = Depends(get_db),
) -> PsychologicalProfileSchema:
    user = await get_user_by_email(session, email)
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


@router.get("/profile/{email}/vector")
async def get_profile_vector(
    email: str,
    session: AsyncSession = Depends(get_db),
):
    user = await get_user_by_email(session, email)
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
        "email": email,
        "user_id": user.id,
        "vector_length": len(profile.profile_vector),
        "vector": profile.profile_vector,
        "completed_at": profile.completed_at.isoformat(),
    }

