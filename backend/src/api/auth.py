from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi.util import get_remote_address

from src.core.email import send_verification_code_email
from src.db.crud.auth import (
    authenticate_user,
    confirm_email_verification_code,
    issue_email_verification_code,
)
from src.api.chat import get_chat_data_for_user
from src.schemas.auth import (
    EmailVerificationConfirmRequest,
    EmailVerificationConfirmResponse,
    EmailVerificationRequest,
    EmailVerificationResponse,
    LoginRequest,
    LoginResponse,
)
from src.schemas.chat import ChatResponse
from src.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def get_limiter(request: Request):
    return request.app.state.limiter


def rate_limit_decorator(limit: str):
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            limiter = get_limiter(request)
            limited_func = limiter.limit(limit)(func)
            return await limited_func(request, *args, **kwargs)
        return wrapper
    return decorator


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    request_data: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> LoginResponse:
    from src.db.crud.auth import get_user_by_username
    from src.core.security import verify_password
    
    # Сначала проверяем существование пользователя и его статус
    user = await get_user_by_username(session, request_data.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    
    # Проверяем, не забанен ли пользователь
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован администратором. Доступ запрещен.",
        )
    
    # Проверяем пароль
    if not verify_password(request_data.password.get_secret_value(), user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    chat_data = await get_chat_data_for_user(session, user.username)

    return LoginResponse(
        username=user.username,
        message=f"Добро пожаловать, {user.full_name or user.username}!",
        chat_data=chat_data.model_dump(),
    )


@router.post(
    "/email/request",
    response_model=EmailVerificationResponse,
    status_code=status.HTTP_200_OK,
)
async def request_email_verification(
    request: Request,
    request_data: EmailVerificationRequest,
    session: AsyncSession = Depends(get_db),
) -> EmailVerificationResponse:
    from src.db.crud.auth import get_user_by_username
    
    # Проверяем, не забанен ли пользователь перед запросом кода
    user_check = await get_user_by_username(session, request_data.username)
    if user_check and not user_check.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован администратором. Доступ запрещен.",
        )
    
    try:
        _, verification_code = await issue_email_verification_code(
            session,
            username=request_data.username,
            email=request_data.email,
            raw_password=request_data.password.get_secret_value(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    await send_verification_code_email(request_data.email, verification_code.code)

    return EmailVerificationResponse(
        message="Код подтверждения отправлен на указанную почту.",
    )


@router.post(
    "/email/confirm",
    response_model=EmailVerificationConfirmResponse,
    status_code=status.HTTP_200_OK,
)
async def confirm_email(
    request: Request,
    request_data: EmailVerificationConfirmRequest,
    session: AsyncSession = Depends(get_db),
) -> EmailVerificationConfirmResponse:
    from src.db.crud.auth import get_user_by_username
    
    # Проверяем, не забанен ли пользователь перед подтверждением email
    user_check = await get_user_by_username(session, request_data.username)
    if user_check and not user_check.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован администратором. Доступ запрещен.",
        )
    
    user = await confirm_email_verification_code(
        session,
        username=request_data.username,
        code=request_data.code,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный или просроченный код подтверждения.",
        )

    chat_data = await get_chat_data_for_user(session, user.username)

    return EmailVerificationConfirmResponse(
        message="Email подтвержден. Теперь вы можете войти по логину и паролю.",
        chat_data=chat_data.model_dump(),
    )
