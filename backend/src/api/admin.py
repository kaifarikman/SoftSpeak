from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.admin_auth import verify_admin, verify_admin_token, get_admin_token
from src.db.session import get_db
from src.db.crud.psychological import (
    get_all_categories,
    get_category_by_id,
    get_questions_by_category,
    get_question_by_id,
)
from src.db.crud import random_names as random_names_crud
from src.db.crud import reports as reports_crud
from src.db.models import Question, Category
from src.schemas.admin import (
    AdminLoginRequest,
    AdminLoginResponse,
    QuestionCreateRequest,
    QuestionUpdateRequest,
    CategoryCreateRequest,
    RandomWordSchema,
    RandomWordCreateRequest,
    RandomWordUpdateRequest,
)
from src.schemas.psychological import QuestionSchema, CategorySchema
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/admin", tags=["admin"])


def get_admin_token(authorization: str | None = Header(None)) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
        )
    
    token = authorization.replace("Bearer ", "").strip()
    
    if not verify_admin_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен",
        )
    
    return token


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(request: AdminLoginRequest) -> AdminLoginResponse:
    if not verify_admin(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    
    from src.core.admin_auth import get_admin_token as get_token_from_settings
    return AdminLoginResponse(
        message="Успешный вход в админку",
        token=get_token_from_settings(),
    )


@router.get("/categories", response_model=list[CategorySchema])
async def get_categories(
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    categories = await get_all_categories(session)
    return [CategorySchema.model_validate(cat) for cat in categories]


@router.post("/categories", response_model=CategorySchema)
async def create_category(
    request: CategoryCreateRequest,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    category = Category(
        name=request.name,
        description=request.description,
        order=request.order,
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return CategorySchema.model_validate(category)


@router.get("/categories/{category_id}/questions", response_model=list[QuestionSchema])
async def get_category_questions(
    category_id: int,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    questions = await get_questions_by_category(session, category_id, only_active=False)
    return [QuestionSchema.model_validate(q) for q in questions]


@router.post("/questions", response_model=QuestionSchema)
async def create_question(
    request: QuestionCreateRequest,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    category = await get_category_by_id(session, request.category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена",
        )
    
    question = Question(
        category_id=request.category_id,
        text=request.text,
        order=request.order,
        is_active=request.is_active,
    )
    session.add(question)
    await session.commit()
    await session.refresh(question)
    return QuestionSchema.model_validate(question)


@router.put("/questions/{question_id}", response_model=QuestionSchema)
async def update_question(
    question_id: int,
    request: QuestionUpdateRequest,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    question = await get_question_by_id(session, question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вопрос не найден",
        )
    
    if request.text is not None:
        question.text = request.text
    if request.order is not None:
        question.order = request.order
    if request.is_active is not None:
        question.is_active = request.is_active
    
    await session.commit()
    await session.refresh(question)
    return QuestionSchema.model_validate(question)


@router.delete("/questions/{question_id}")
async def delete_question(
    question_id: int,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    question = await get_question_by_id(session, question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вопрос не найден",
        )
    
    await session.delete(question)
    await session.commit()
    return {"message": "Вопрос удален"}


@router.get("/random-names/adjectives", response_model=list[RandomWordSchema])
async def list_random_adjectives(
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    words = await random_names_crud.list_adjectives(session)
    return [RandomWordSchema.model_validate(word) for word in words]


@router.post("/random-names/adjectives", response_model=RandomWordSchema)
async def create_random_adjective(
    request: RandomWordCreateRequest,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    try:
        word = await random_names_crud.create_adjective(session, request.text)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return RandomWordSchema.model_validate(word)


@router.put("/random-names/adjectives/{word_id}", response_model=RandomWordSchema)
async def update_random_adjective(
    word_id: int,
    request: RandomWordUpdateRequest,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    word = await random_names_crud.get_adjective(session, word_id)
    if not word:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Прилагательное не найдено")
    try:
        updated = await random_names_crud.update_adjective(
            session,
            word,
            text=request.text,
            is_active=request.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return RandomWordSchema.model_validate(updated)


@router.delete("/random-names/adjectives/{word_id}")
async def delete_random_adjective(
    word_id: int,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    word = await random_names_crud.get_adjective(session, word_id)
    if not word:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Прилагательное не найдено")
    await random_names_crud.delete_adjective(session, word)
    return {"message": "Прилагательное удалено"}


@router.get("/random-names/nouns", response_model=list[RandomWordSchema])
async def list_random_nouns(
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    words = await random_names_crud.list_nouns(session)
    return [RandomWordSchema.model_validate(word) for word in words]


@router.post("/random-names/nouns", response_model=RandomWordSchema)
async def create_random_noun(
    request: RandomWordCreateRequest,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    try:
        word = await random_names_crud.create_noun(session, request.text)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return RandomWordSchema.model_validate(word)


@router.put("/random-names/nouns/{word_id}", response_model=RandomWordSchema)
async def update_random_noun(
    word_id: int,
    request: RandomWordUpdateRequest,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    word = await random_names_crud.get_noun(session, word_id)
    if not word:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Существительное не найдено")
    try:
        updated = await random_names_crud.update_noun(
            session,
            word,
            text=request.text,
            is_active=request.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return RandomWordSchema.model_validate(updated)


@router.delete("/random-names/nouns/{word_id}")
async def delete_random_noun(
    word_id: int,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    word = await random_names_crud.get_noun(session, word_id)
    if not word:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Существительное не найдено")
    await random_names_crud.delete_noun(session, word)
    return {"message": "Существительное удалено"}


class ReportSchema(BaseModel):
    id: int
    reporter_id: int
    reported_user_id: int
    chat_id: int
    reason: str
    description: Optional[str]
    status: str
    created_at: str
    resolved_at: Optional[str]
    resolved_by_admin_id: Optional[int]
    reporter_username: Optional[str] = None
    reported_user_username: Optional[str] = None

    class Config:
        from_attributes = True


class AdminActionResponse(BaseModel):
    success: bool
    message: str


@router.get("/reports", response_model=list[ReportSchema])
async def get_all_reports(
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
) -> list[ReportSchema]:
    from sqlalchemy import select
    from src.db.models import User
    
    reports = await reports_crud.get_all_reports(session, status=status)
    
    result = []
    for report in reports:
        reporter_stmt = select(User).where(User.id == report.reporter_id)
        reporter_result = await session.execute(reporter_stmt)
        reporter = reporter_result.scalar_one_or_none()
        
        reported_user_stmt = select(User).where(User.id == report.reported_user_id)
        reported_user_result = await session.execute(reported_user_stmt)
        reported_user = reported_user_result.scalar_one_or_none()
        
        result.append(ReportSchema(
            id=report.id,
            reporter_id=report.reporter_id,
            reported_user_id=report.reported_user_id,
            chat_id=report.chat_id,
            reason=report.reason,
            description=report.description,
            status=report.status,
            created_at=report.created_at.isoformat(),
            resolved_at=report.resolved_at.isoformat() if report.resolved_at else None,
            resolved_by_admin_id=report.resolved_by_admin_id,
            reporter_username=reporter.username if reporter else None,
            reported_user_username=reported_user.username if reported_user else None,
        ))
    
    return result


@router.get("/reports/{report_id}/chat")
async def get_report_chat_messages(
    report_id: int,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    from src.db.crud.reports import get_report_by_id
    from sqlalchemy import select
    from src.db.models import AnonymousChat, AnonymousMessage
    from sqlalchemy.orm import selectinload
    
    report = await get_report_by_id(session, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Жалоба не найдена",
        )
    
    chat_stmt = (
        select(AnonymousChat)
        .where(AnonymousChat.id == report.chat_id)
        .options(selectinload(AnonymousChat.messages))
    )
    chat_result = await session.execute(chat_stmt)
    chat = chat_result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден",
        )
    
    return {
        "chat_id": report.chat_id,
        "messages": [
            {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "is_read": msg.is_read,
            }
            for msg in chat.messages
        ],
    }


@router.post("/reports/{report_id}/ban", response_model=AdminActionResponse)
async def ban_user_from_report(
    report_id: int,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
) -> AdminActionResponse:
    from src.core.config import settings
    from src.db.crud.auth import get_user_by_nickname
    
    admin_user = await get_user_by_nickname(session, settings.admin_username)
    admin_id = admin_user.id if admin_user else None
    
    success, error_message = await reports_crud.ban_user_from_report(
        session,
        report_id=report_id,
        admin_id=admin_id,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message or "Ошибка бана пользователя",
        )
    
    return AdminActionResponse(
        success=True,
        message="Пользователь забанен",
    )


@router.post("/reports/{report_id}/reject", response_model=AdminActionResponse)
async def reject_report(
    report_id: int,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
) -> AdminActionResponse:
    from src.core.config import settings
    from src.db.crud.auth import get_user_by_nickname
    
    admin_user = await get_user_by_nickname(session, settings.admin_username)
    admin_id = admin_user.id if admin_user else None
    
    success, error_message = await reports_crud.reject_report(
        session,
        report_id=report_id,
        admin_id=admin_id,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message or "Ошибка отклонения жалобы",
        )
    
    return AdminActionResponse(
        success=True,
        message="Жалоба отклонена",
    )

