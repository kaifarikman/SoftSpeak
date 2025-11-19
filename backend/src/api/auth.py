from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

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


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request_data: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Базовая ручка авторизации по username/password."""

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

    # Получаем данные чата для пользователя
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
    request_data: EmailVerificationRequest,
    session: AsyncSession = Depends(get_db),
) -> EmailVerificationResponse:
    """Запрашивает код подтверждения email и отправляет его пользователю."""
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
    request_data: EmailVerificationConfirmRequest,
    session: AsyncSession = Depends(get_db),
) -> EmailVerificationConfirmResponse:
    """Подтверждает код из письма и активирует пользователя."""

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

    # После подтверждения email также возвращаем данные чата
    chat_data = await get_chat_data_for_user(session, user.username)

    return EmailVerificationConfirmResponse(
        message="Email подтвержден. Теперь вы можете войти по логину и паролю.",
        chat_data=chat_data.model_dump(),
    )
