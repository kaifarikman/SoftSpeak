"""API эндпоинты для админки."""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.admin_auth import verify_admin, verify_admin_token, ADMIN_TOKEN
from src.db.session import get_db
from src.db.crud.psychological import (
    get_all_categories,
    get_category_by_id,
    get_questions_by_category,
    get_question_by_id,
)
from src.db.crud import random_names as random_names_crud
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

router = APIRouter(prefix="/admin", tags=["admin"])


def get_admin_token(authorization: str = Header(None)) -> str:
    """Проверяет токен админа из заголовка."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
        )
    
    # Формат: "Bearer token" или просто "token"
    token = authorization.replace("Bearer ", "").strip()
    
    if not verify_admin_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен",
        )
    
    return token


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(request: AdminLoginRequest) -> AdminLoginResponse:
    """Вход в админку."""
    if not verify_admin(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    
    return AdminLoginResponse(
        message="Успешный вход в админку",
        token=ADMIN_TOKEN,
    )


@router.get("/categories", response_model=list[CategorySchema])
async def get_categories(
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    """Получает все категории."""
    categories = await get_all_categories(session)
    return [CategorySchema.model_validate(cat) for cat in categories]


@router.post("/categories", response_model=CategorySchema)
async def create_category(
    request: CategoryCreateRequest,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    """Создает новую категорию."""
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
    """Получает вопросы категории."""
    questions = await get_questions_by_category(session, category_id, only_active=False)
    return [QuestionSchema.model_validate(q) for q in questions]


@router.post("/questions", response_model=QuestionSchema)
async def create_question(
    request: QuestionCreateRequest,
    session: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token),
):
    """Создает новый вопрос."""
    # Проверяем существование категории
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
    """Обновляет вопрос."""
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
    """Удаляет вопрос."""
    question = await get_question_by_id(session, question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вопрос не найден",
        )
    
    await session.delete(question)
    await session.commit()
    return {"message": "Вопрос удален"}


# ------------------- Random aliases ------------------- #


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

