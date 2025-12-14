# SoftSpeak

Платформа для анонимных чатов с автоматическим подбором собеседников на основе психологического профиля.

## Описание

SoftSpeak позволяет пользователям общаться анонимно с автоматически подобранными собеседниками. Система использует машинное обучение для создания векторных профилей пользователей на основе их ответов на психологические вопросы и подбора наиболее совместимых пар.

## Технологический стек

- **Backend**: FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **Frontend**: React 18, Vite, Nginx
- **ML Service**: PyTorch, sentence-transformers
- **Infrastructure**: Docker Compose

## Быстрый старт

### Требования

- Docker и Docker Compose
- Git

### Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd SoftSpeak
```

2. Создайте файл `.env` в корне проекта:
```env
POSTGRES_USER=softspeak_user
POSTGRES_PASSWORD=softspeak_pass
POSTGRES_DB=softspeak_db
JWT_SECRET=your-secret-key-minimum-32-characters-long
ML_MODEL_NAME=intfloat/multilingual-e5-base
DEV_MODE=true
```

3. Запустите проект:
```bash
docker-compose up -d --build
```

При первом запуске ML-сервис скачает модель (~500 МБ), это может занять 5-10 минут.

### Доступ к сервисам

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API документация: http://localhost:8000/docs
- Admin панель: http://localhost:3000/admin (admin/admin)
- MailHog (разработка): http://localhost:8025

## Основные команды

```bash
# Запуск всех сервисов
docker-compose up -d

# Остановка всех сервисов
docker-compose down

# Просмотр логов
docker-compose logs -f backend

# Пересборка конкретного сервиса
docker-compose up -d --build backend

# Выполнение миграций
docker-compose exec backend alembic upgrade head

# Сброс базы данных
docker-compose down -v
```

## Переменные окружения

### База данных
- `POSTGRES_USER` - пользователь PostgreSQL
- `POSTGRES_PASSWORD` - пароль PostgreSQL
- `POSTGRES_DB` - имя базы данных

### Безопасность
- `JWT_SECRET` - секретный ключ для JWT токенов (минимум 32 символа)
- `ADMIN_USERNAME` - имя пользователя админ-панели
- `ADMIN_PASSWORD` - пароль админ-панели
- `ADMIN_TOKEN` - токен для админ API

### Email (продакшен)
- `DEV_MODE` - режим разработки (true/false)
- `EMAIL_FROM` - email отправителя
- `SMTP_HOST` - SMTP сервер
- `SMTP_PORT` - SMTP порт
- `SMTP_USER` - SMTP пользователь
- `SMTP_PASSWORD` - SMTP пароль
- `SMTP_USE_TLS` - использовать TLS

### ML Service
- `ML_MODEL_NAME` - название модели для эмбеддингов

## Структура проекта

```
SoftSpeak/
├── backend/          # FastAPI backend
│   ├── src/
│   │   ├── api/     # API endpoints
│   │   ├── db/      # Models и CRUD операции
│   │   ├── core/    # Конфигурация, безопасность
│   │   └── schemas/ # Pydantic схемы
│   └── Dockerfile
├── frontend/         # React frontend
│   ├── src/
│   │   ├── components/  # React компоненты
│   │   ├── pages/       # Страницы приложения
│   │   └── utils/       # Утилиты
│   └── Dockerfile
├── ml/               # ML сервис
│   ├── services/    # Embeddings и matching
│   └── Dockerfile
└── docker-compose.yml
```

## Основной функционал

### Аутентификация
- Регистрация с подтверждением email
- JWT токены для авторизации
- Автоматическое приветствие от бота после регистрации

### Психологический профиль
- WebSocket опрос для новых пользователей
- Создание векторных профилей через ML модель
- Автоматический подбор собеседников по совместимости

### Анонимные чаты
- Мгновенный поиск собеседника
- Случайные алиасы для пользователей
- WebSocket для сообщений в реальном времени
- Отправка медиа файлов

### Публичные чаты
- Переход из анонимных чатов при обоюдном согласии
- Отображение реальных имен и аватаров
- Сохранение истории сообщений

### Настройки
- Профиль пользователя (аватар, био, никнейм)
- Настройки уведомлений
- Управление медиа
- Черный список

### Админ панель
- Управление вопросами опроса
- Управление случайными именами
- Просмотр статистики

## Лицензия

Проект находится в разработке.
