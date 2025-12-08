from fastapi import FastAPI, WebSocket, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.api.auth import router as auth_router
from src.api.chat import router as chat_router
from src.api.admin import router as admin_router
from src.api.psychological import router as psychological_router
from src.api.websocket_survey import websocket_survey_endpoint
from src.api.matchmaking import router as matchmaking_router
from src.api.settings import router as settings_router
from src.api.reports import router as reports_router
from src.api.notifications import router as notifications_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="SoftSpeak API",
    description="API для аутентификации SoftSpeak",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    logger.error(f"Validation error: {errors}")
    
    # Форматируем ошибки для клиента
    formatted_errors = []
    for error in errors:
        # Извлекаем сообщение об ошибке
        msg = error.get("msg", "")
        # Если msg - это список или словарь, извлекаем строку
        if isinstance(msg, (list, tuple)) and len(msg) > 0:
            msg = str(msg[0])
        elif isinstance(msg, dict):
            # Если это словарь, пытаемся извлечь сообщение
            msg = msg.get("msg", str(msg))
        else:
            msg = str(msg)
        
        # Извлекаем ctx (контекст ошибки), если есть
        ctx = error.get("ctx", {})
        if ctx and isinstance(ctx, dict):
            # Если в ctx есть информация об ошибке, используем её
            if "error" in ctx:
                error_obj = ctx["error"]
                if isinstance(error_obj, Exception):
                    msg = str(error_obj)
        
        error_dict = {
            "loc": list(error.get("loc", [])),
            "msg": msg,
            "type": str(error.get("type", "validation_error"))
        }
        formatted_errors.append(error_dict)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": formatted_errors},
    )


@app.on_event("startup")
async def startup_event():
    logger.info("Запуск приложения...")
    from src.api.websocket_survey import start_retry_task
    start_retry_task()
    logger.info("Приложение запущено.")

from src.core.config import settings

cors_origins_list = [
    origin.strip() 
    for origin in settings.cors_origins.split(",") 
    if origin.strip()
]

if settings.cors_origins.strip() == "*":
    cors_origins_list = ["*"]
else:
    if "*" in cors_origins_list and len(cors_origins_list) > 1:
        logger.warning("CORS: '*' игнорируется при наличии других origins")
        cors_origins_list = [o for o in cors_origins_list if o != "*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from slowapi.middleware import SlowAPIMiddleware
app.add_middleware(SlowAPIMiddleware)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(psychological_router)
app.include_router(matchmaking_router)
app.include_router(settings_router)
app.include_router(reports_router)
app.include_router(notifications_router)


@app.get("/")
async def root():
    return {"message": "Hello"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.websocket("/ws/survey/{username}")
async def websocket_survey(websocket: WebSocket, username: str):
    await websocket_survey_endpoint(websocket, username)
