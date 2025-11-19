"""Настройка async сессии SQLAlchemy."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.core.config import settings

# Создаем async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Установить True для отладки SQL запросов
    future=True,
)

# Создаем фабрику сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """
    Зависимость для получения async сессии БД.
    
    Примечание: CRUD функции сами управляют коммитами.
    Если в обработчике происходит ошибка, сессия автоматически откатывается
    при выходе из контекста (если не было commit).
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            # Откатываем транзакцию при ошибке (если не было commit)
            await session.rollback()
            raise

