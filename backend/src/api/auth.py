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
    """Получает limiter из состояния приложения."""
    return request.app.state.limiter


def rate_limit_decorator(limit: str):
    """Создает декоратор для rate limiting с использованием limiter из app.state."""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            limiter = get_limiter(request)
            # Применяем декоратор limiter к функции
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
    # Rate limiting обрабатывается через SlowAPIMiddleware
    # Для специфичных лимитов можно добавить дополнительную проверку
    user = await authenticate_user(
        session,
        request_data.username,
        request_data.password.get_secret_value(),
    )

    if not user:
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
    # Rate limiting обрабатывается через SlowAPIMiddleware
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
    # Rate limiting обрабатывается через SlowAPIMiddleware
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
