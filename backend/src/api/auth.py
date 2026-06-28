from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    Response,
    Cookie,
    Header,
)
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
from src.core.config import settings
from src.core.email import send_verification_code_email
from src.core.security import create_access_token, create_refresh_token, decode_jwt_token
from src.db.crud.auth import (
    authenticate_user,
    confirm_email_verification_code,
    issue_email_verification_code,
    get_user_by_email,
    get_user_by_nickname,
)
from src.api.chat import get_chat_data_for_user
from src.schemas.auth import (
    AuthMeResponse,
    EmailVerificationConfirmRequest,
    EmailVerificationConfirmResponse,
    EmailVerificationRequest,
    EmailVerificationResponse,
    LoginRequest,
    LoginResponse,
    TokenResponse,
    get_allowed_email_domains,
)
from src.schemas.chat import ChatResponse
from src.db.session import get_db
from src.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_COOKIE_NAME = "softspeak_refresh"
EMAIL_REQUEST_LIMIT = 5
EMAIL_REQUEST_WINDOW_SECONDS = 60 * 60
_email_request_attempts: dict[str, deque[datetime]] = defaultdict(deque)


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=int(timedelta(days=settings.jwt_refresh_ttl_days).total_seconds()),
        httponly=True,
        secure=not settings.dev_mode,
        samesite="lax",
        path="/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/auth")


async def get_current_user(
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_jwt_token(token, "access")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    user = await get_user_by_email(session, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован администратором. Доступ запрещен.",
        )
    return user


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


def _enforce_email_request_limit(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    now = datetime.now(timezone.utc)
    attempts = _email_request_attempts[client_host]
    while attempts and (now - attempts[0]).total_seconds() >= EMAIL_REQUEST_WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= EMAIL_REQUEST_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов. Попробуйте позже.",
        )
    attempts.append(now)


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    response: Response,
    request_data: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> LoginResponse:
    user = await authenticate_user(
        session, request_data.email, request_data.password.get_secret_value()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль"
        )
    chat_data = await get_chat_data_for_user(session, user.email)
    access_token = create_access_token(user.email)
    refresh_token = create_refresh_token(user.email)
    set_refresh_cookie(response, refresh_token)
    return LoginResponse(
        nickname=user.nickname,
        email=user.email,
        access_token=access_token,
        message=f"Добро пожаловать, {user.full_name or user.nickname}!",
        chat_data=chat_data.model_dump(),
    )


@router.get("/email/domains", response_model=list[str], status_code=status.HTTP_200_OK)
async def get_email_domains() -> list[str]:
    return sorted(get_allowed_email_domains())


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_access_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token отсутствует",
        )
    try:
        payload = decode_jwt_token(refresh_token, "refresh")
    except ValueError as exc:
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    user = await get_user_by_email(session, payload["sub"])
    if not user or not user.is_active:
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    if user.is_banned:
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован администратором. Доступ запрещен.",
        )
    new_refresh_token = create_refresh_token(user.email)
    set_refresh_cookie(response, new_refresh_token)
    return TokenResponse(access_token=create_access_token(user.email))


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response) -> dict:
    clear_refresh_cookie(response)
    return {"message": "Вы вышли из системы"}


@router.get("/me", response_model=AuthMeResponse, status_code=status.HTTP_200_OK)
async def get_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AuthMeResponse:
    chat_data = await get_chat_data_for_user(session, current_user.email)
    return AuthMeResponse(
        nickname=current_user.nickname,
        email=current_user.email,
        chat_data=chat_data.model_dump(),
        is_banned=current_user.is_banned,
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
    _enforce_email_request_limit(request)
    user_check = await get_user_by_nickname(session, request_data.nickname)
    if user_check and user_check.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован администратором. Доступ запрещен.",
        )
    try:
        _, verification_code = await issue_email_verification_code(
            session,
            nickname=request_data.nickname,
            email=request_data.email,
            raw_password=request_data.password.get_secret_value(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await send_verification_code_email(request_data.email, verification_code.code)
    return EmailVerificationResponse(
        message="Код подтверждения отправлен на указанную почту."
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
    user_check = await get_user_by_nickname(session, request_data.nickname)
    if user_check and user_check.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован администратором. Доступ запрещен.",
        )
    user = await confirm_email_verification_code(
        session, nickname=request_data.nickname, code=request_data.code
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный или просроченный код подтверждения.",
        )
    chat_data = await get_chat_data_for_user(session, user.email)
    return EmailVerificationConfirmResponse(
        message="Email подтвержден. Теперь вы можете войти по логину и паролю.",
        chat_data=chat_data.model_dump(),
    )
