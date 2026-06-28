# SoftSpeak — Roadmap до идеала

## 🔴 P0 — Критично (блокирует продакшн)

### DevOps (выполнено)
- [x] Починить `requires-python = ">=3.14"` → `>=3.11` в `backend/pyproject.toml`
- [x] Убрать захардкоженный `sqlalchemy.url` из `backend/src/alembic.ini`
- [x] Починить `proxy_connect_timeout 7d` (невалидный синтаксис) в `frontend/nginx.conf`
- [x] Создать Alembic migrations структуру (`backend/src/app/migrations/` + `0001_initial.py`)
- [x] Создать `backend/static/` директорию
- [x] Создать `.env` файл для локальной разработки
- [x] Убрать `--reload` из `docker-compose.yml` backend command

### Безопасность
- [x] **JWT refresh token** — добавить `POST /auth/refresh`, хранить refresh в httpOnly cookie; сейчас AT живёт 30 мин и пользователь вылетает из системы
- [x] **Права доступа из localStorage → с бэка** — `chat_data` (ai/messengers/settings) хранится на клиенте и может быть подделан; права должны приходить с бэка через `GET /auth/me`
- [x] **CORS** — заменить `CORS_ORIGINS=*` на конкретные домены через env; сейчас любой сайт может делать запросы к API
- [x] **Admin дефолты** — убрать `ADMIN_PASSWORD=admin` из `docker-compose.yml`; требовать явной установки через `.env`
- [x] **`.gitignore`** — убедиться что `.env` не попадёт в репозиторий

### Стабильность
- [x] **Fallback при недоступном ML** — бэк возвращает 500 когда ML сервис не поднялся; нужен `503` с понятным сообщением; фронт — показывать "матчмейкинг временно недоступен"
- [x] **`/health` эндпоинт** — проверить что он реально существует в `backend/src/main.py`; docker-compose делает на него healthcheck

---

## 🟠 P1 — Важно (качество продукта)

### Архитектура бэкенда
- [x] **Разбить `matchmaking.py`** (1102 строки) — выделить: `queue.py` (логика очереди), `match.py` (поиск матча), `ws_handler.py` (WebSocket обработчик)
- [x] **Разбить `websocket_survey.py`** (537 строк) — выделить логику вопросов в `survey_service.py`
- [x] **Email domain whitelist** — захардкожен в `SignUp.jsx` И в `backend/src/api/auth.py`; вынести в env переменную `ALLOWED_EMAIL_DOMAINS`

### Архитектура фронтенда
- [x] **Разбить `Admin.jsx`** (736 строк) — компоненты: `QuestionsPanel`, `ReportsPanel`, `NamesPanel`, `BannedPanel`, `StatsPanel`
- [x] **Разбить `Messenger.jsx`** (494 строки) — по разделам: `BotSection`, `AnonSection`, `PeopleSection`, `SettingsSection`
- [x] **`FirstStart.jsx`** — страница существует но не подключена к роутингу; либо интегрировать в флоу регистрации, либо удалить

### UX
- [x] **Индикатор загрузки ML** — при старте системы матчмейкинг недоступен 10–30 мин; показывать пользователю статус вместо ошибки
- [x] **Автообновление JWT** — добавить interceptor в `apiHelper.js` который рефрешит токен при `401` вместо выброса пользователя

---

## 🟡 P2 — Улучшения (polish)

### Тесты
- [x] Integration тесты auth flow — регистрация → верификация → логин (`pytest` + `httpx AsyncClient`)
- [x] Integration тесты matchmaking — join queue → match found → chat created
- [x] Unit тесты ML сервиса — embedding dimensions, cosine similarity edge cases
- [x] Frontend smoke tests — `Vitest` или `Playwright` для критических страниц

### Инфраструктура
- [x] **Pre-download ML модели** в Docker образ — убрать 30-мин ожидание при деплое; добавить в `ml/Dockerfile`:
  ```dockerfile
  RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-base')"
  ```
- [x] Пагинация chat lists — `GET /chat/data/{email}` отдаёт все чаты сразу; добавить `?page=&limit=`
- [x] Rate limiting на WebSocket endpoints — сейчас slowapi только на HTTP

### Бэкенд
- [x] Pagination для сообщений — `GET /chat/{id}/messages?before=&limit=50` для бесконечной прокрутки
- [x] Поиск по чатам — `GET /chat/search?q=` для ChatList
- [x] Structured logging — JSON формат с уровнями для продакшена
- [x] Alembic autogenerate — настроить `alembic revision --autogenerate` чтобы будущие миграции генерировались автоматически

---

## 🔵 P3 — Фичи (будущее)

- [x] Push уведомления — Web Push / PWA для уведомлений об анонимных чатах
- [x] Аватары пользователей — загрузка и хранение (S3 или `/static/avatars/`)
- [x] Блэклист пользователей — упоминается в настройках, логика не реализована
- [x] Mobile-first — `HamburgerMenu` компонент есть, адаптивность не протестирована
- [x] Профиль пользователя — страница `/u/{nickname}` с публичным профилем
