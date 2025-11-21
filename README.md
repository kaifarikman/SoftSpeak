# SoftSpeak

Платформа анонимных чатов с автоматическим подбором собеседников на основе психологического профиля. Состоит из трех сервисов: backend (FastAPI), frontend (React), ML (embeddings + matching).

## Функционал

**Auth & Registration**
- Email verification (MailHog для разработки)
- JWT-токены
- Автоматическое приветствие от бота после регистрации

**Psychological Profiling**
- WebSocket-опрос для новых пользователей
- Векторные профили через `intfloat/multilingual-e5-base`
- ML-матчинг по косинусной близости

**Anonymous Chats**
- Мгновенный поиск собеседника
- Случайные алиасы из БД ("Смелый Сокол", и т.д.)
- Двухсторонняя логика: оба пользователя должны согласиться для перехода в публичный чат
- Отправка фото/видео (опционально в настройках)
- WebSocket для сообщений в реальном времени

**Public Chats**
- Автоматический перенос из анонимных при обоюдном согласии
- Отображение реальных имен и аватаров
- Сохранение истории сообщений

**Settings**
- Avatar, bio, username
- Уведомления
- Медиа (фото/видео)
- Смена пароля
- Черный список

**Admin Panel**
- Управление вопросами опроса
- CRUD для случайных имен (прилагательные, существительные)
- Статистика

## Стек

- **Backend**: FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **Frontend**: React 18, Vite, Nginx
- **ML**: PyTorch, sentence-transformers
- **Infra**: Docker Compose, MailHog

```
Browser → Nginx → /api → Backend → PostgreSQL / ML
                  /ws → WebSocket
                  /static → uploads (avatars, media)
```

## Быстрый старт

```bash
git clone <repo-url>
cd SoftSpeak
```

Создайте `.env` (см. `.env.example`):
```env
POSTGRES_USER=softspeak_user
POSTGRES_PASSWORD=softspeak_pass
POSTGRES_DB=softspeak_db
JWT_SECRET=your-secret-key-min-32-chars
ML_MODEL_NAME=intfloat/multilingual-e5-base
```

Запуск:
```bash
docker-compose up -d --build
```

ML-сервис скачает ~500 МБ модели при первом старте (5-10 минут).

**Доступ:**
- http://localhost:3000 — фронт
- http://localhost:3000/admin — админка (admin/admin)
- http://localhost:8000/docs — Swagger
- http://localhost:8025 — MailHog

## Команды

```bash
# Остановить
docker-compose down

# Сбросить БД
docker-compose down -v && docker volume rm softspeak_postgres_data || true

# Пересобрать
docker-compose up -d --build backend

# Логи
docker-compose logs -f backend

# Миграции
docker-compose exec backend alembic upgrade head
```

## Переменные окружения

Основные:
- `POSTGRES_*` — настройки БД
- `JWT_SECRET` — ключ токенов (32+ символа)
- `SMTP_*` — email для прода
- `ML_MODEL_NAME` — модель эмбеддингов
- `ADMIN_USERNAME`, `ADMIN_PASSWORD` — доступ к админке

Полный список в `.env.example`.

## Структура

```
backend/src/
├── api/          auth, matchmaking, chat, settings, admin
├── db/           models, crud operations
├── core/         config, security, email
└── schemas/      pydantic models

frontend/src/
├── components/   messenger UI (ChatArea, MessageInput, etc.)
├── pages/        Landing, SignIn, Messenger, Admin
├── context/      ChatDataContext
└── css/          styles

ml/services/      embeddings, matching, cosine distance
```

**Backend ключевые файлы:**
- `api/matchmaking.py` — WebSocket matchmaking, reveal logic, media upload
- `db/models.py` — User, AnonymousChat, Message, Question, RandomName*
- `db/crud/matchmaking.py` — find_match, reveal_anonymous_chat

**Frontend ключевые файлы:**
- `components/messenger/ChatArea.jsx` — WebSocket чат
- `context/ChatDataContext.jsx` — глобальное состояние
- `pages/Admin.jsx` — админка вопросов и алиасов

**ML:**
- `services/embedding.py` — векторизация текста
- `services/matching.py` — подбор по косинусной близости

## Основные потоки

**Регистрация:**
1. Email verification (код в MailHog)
2. Автовход после подтверждения
3. Приветственное сообщение от бота
4. WebSocket-опрос
5. Сохранение векторного профиля

**Matchmaking:**
1. Кнопка "Смэтчиться" → в очередь
2. ML-сервис вычисляет совместимость
3. Создание анонимного чата
4. WebSocket уведомления обоим пользователям

**Reveal:**
1. Один пользователь жмет "Раскрыться"
2. WebSocket-запрос второму
3. Второй соглашается
4. Чат переносится в публичные с реальными именами
