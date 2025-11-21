from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging

from src.api.auth import router as auth_router
from src.api.chat import router as chat_router
from src.api.admin import router as admin_router
from src.api.psychological import router as psychological_router
from src.api.websocket_survey import websocket_survey_endpoint
from src.api.matchmaking import router as matchmaking_router
from src.api.settings import router as settings_router

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SoftSpeak API",
    description="API для аутентификации SoftSpeak",
    version="0.1.0",
)


@app.on_event("startup")
async def startup_event():
    """Инициализация приложения."""
    logger.info("Запуск приложения...")
    logger.info("Приложение запущено.")

# Подключаем статические файлы для админ-панели и аватаров
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Создаем директорию для загрузки аватаров
uploads_dir = static_dir / "uploads" / "avatars"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(psychological_router)
app.include_router(matchmaking_router)
app.include_router(settings_router)


@app.get("/")
async def root():
    """Корневой эндпоинт."""

    return {"message": "Hello"}


@app.get("/health")
async def health():
    """Health check эндпоинт."""

    return {"status": "ok"}


@app.websocket("/ws/survey/{username}")
async def websocket_survey(websocket: WebSocket, username: str):
    """WebSocket эндпоинт для опроса."""
    await websocket_survey_endpoint(websocket, username)
