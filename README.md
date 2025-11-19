# 🗣️ SoftSpeak

SoftSpeak — это платформа анонимного общения с ML-профилированием, мгновенным подбором собеседников и возможностью «раскрытия» диалога в публичный чат по обоюдному согласию. Проект состоит из трех сервисов (backend, frontend и ML) и полностью разворачивается через Docker.

## 💡 Основные возможности

- Психологический опрос и формирование совместимого профиля пользователя
- ML-матчинг на основе `intfloat/multilingual-e5-base` и косинусной близости
- Анонимные чаты с WebSocketами и matchmaking в реальном времени
- Двухсторонняя логика «Раскрыться»: запрос → подтверждение → перенос чата в публичный раздел
- Публичные чаты без задержек, общий WebSocket-стек для анонимных и открытых диалогов
- Мгновенное приветственное сообщение от бота после регистрации (без обновления страницы)
- Очистка локального состояния при смене аккаунта, чтобы старые чаты не подтягивались
- Загрузка аватара через настройки и мгновенное отображение в навигации и публичных чатах
- Разграничение разделов интерфейса (бот, анонимные диалоги, публичные чаты, настройки)

## 🧱 Архитектура и стек

| Сервис | Технологии | Роль |
|--------|-----------|------|
| Backend | FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis (опционально), WebSockets | Rest API, matchmaking, хранение данных, файловый сервер |
| Frontend | React 18 + Vite, Context API, WebSocket-клиенты, Nginx | SPA-интерфейс, управление состоянием чатов, загрузка файлов |
| ML Service | FastAPI, PyTorch, sentence-transformers | Построение эмбеддингов и оценка совместимости |
| Инфраструктура | Docker Compose, MailHog, volumes, healthchecks | Отдельные контейнеры, проксирование `/api`, `/ws`, `/static` |

```
Browser → (Nginx фронтенда) → /api → FastAPI → PostgreSQL / ML
                               \→ /ws  → WebSocket эндпоинты
                               \→ /static → медиа-файлы (аватары)
```

## 🚀 Быстрый старт

1. **Клонируем репозиторий**:
   ```bash
   git clone <repo-url>
   cd SoftSpeak
   ```
2. **Создаем `.env`** (см. `.env.example`). Минимум:
   ```env
   POSTGRES_USER=softspeak_user
   POSTGRES_PASSWORD=softspeak_pass
   POSTGRES_DB=softspeak_db
   JWT_SECRET=измените-ключ
   ML_MODEL_NAME=intfloat/multilingual-e5-base
   ```
3. **Запускаем сервисы**:
   ```bash
   docker-compose up -d --build
   ```
   > ML-сервису нужно скачать ~500 МБ модели; первый старт занимает 5–10 минут.
4. **Открываем**:
   - http://localhost:3000 — интерфейс
   - http://localhost:8000/docs — Swagger
   - http://localhost:8025 — MailHog

## ⚙️ Ежедневные команды

| Действие | Команда |
|----------|---------|
| Остановить все | `docker-compose down` |
| Остановить c очисткой volume | `docker-compose down -v` |
| Перезапустить сервис | `docker-compose restart frontend` |
| Пересобрать сервис | `docker-compose up -d --build backend` |
| Смотреть логи | `docker-compose logs -f backend` |
| Сбросить БД до нуля | `docker-compose down -v && docker volume rm softspeak_postgres_data || true && docker-compose up -d` |
| Очистить таблицы без удаления volume | `docker-compose exec db psql -U softspeak_user -d softspeak_db -c "TRUNCATE TABLE <tables> RESTART IDENTITY CASCADE;"` |

## 🔐 Переменные окружения

| Переменная | Назначение |
|-----------|------------|
| `POSTGRES_*` | Конфигурация БД |
| `JWT_SECRET` | Подпись токенов (минимум 32 символа) |
| `SMTP_*` | Отправка email (для продакшена) |
| `ML_MODEL_NAME` | Название модели эмбеддингов |
| `BACKEND_PORT`, `FRONTEND_PORT`, `ML_SERVICE_PORT` | Порты сервисов |

Полный список — в `.env.example`.

## 🗂️ Структура репозитория

```
backend/          # FastAPI, SQLAlchemy, миграции
frontend/         # React + Vite + Nginx
ml/               # ML сервис FastAPI
docker-compose.yml
README.md         # этот файл
PROJECT_STRUCTURE.md
QUICKSTART.md
CHANGELOG.md
SETTINGS_FEATURE.md / FIXES_APPLIED.md — история задач
```

### Backend `src/`
- `api/` — модули `auth`, `matchmaking`, `settings`, WebSocket для опроса
- `db/models.py` — пользователи, чаты, профили, поля `is_public`, `user*_revealed`
- `db/crud/matchmaking.py` — очереди, reveal-логика, публичные чаты
- `core/config.py`, `security.py`, `email.py`
- `services/vector_utils.py` — интеграция с ML
- `main.py` — запуск, CORS, StaticFiles, роутеры

### Frontend `src/`
- `context/ChatDataContext.jsx` — синхронизация `chat_data` через `localStorage` + `chatDataUpdated`
- `pages/Messenger.jsx` — переключение разделов, очистка состояний при смене пользователя
- `components/messenger/*` — чаты, списки, `MatchmakingButton`, `Navigation`, `SettingsContent`
- `config.js` — `/api` и `/ws` относительные пути
- `css/components/*.css` — стили, включая кнопку «Раскрыться»

### ML `services/`
- `embedding.py`, `matching.py`, `cosine_distance_func.py`
- FastAPI эндпоинты `/embedding`, `/profile-vector`, `/best-match`

## 🧪 Диагностика и отладка

- **Swagger**: `http://localhost:8000/docs`
- **Проверка сервисов**: `docker-compose ps`
- **Состояние ML**: `curl http://localhost:8001/health`
- **WebSocket matchmaking**: `ws://localhost:8000/matchmaking/ws/{username}`
- **Проблемы с аватарами**: убедитесь, что браузер запрашивает `/static/uploads/...`, а не `/api/static/...`; контейнер front нужно пересобрать (`docker-compose up -d --build frontend`)

## 🧩 Недавние доработки

- Восстановлены приветственные сообщения бота сразу после регистрации (событие `chatDataUpdated`)
- Полная очистка локального состояния при смене аккаунта
- Оптимизации matchmaking: троттлинг в UI, увеличенные интервалы на backend
- Двухфазное раскрытие чатов с хранением флагов `user*_revealed`, перенос в публичный раздел и уведомлениями по WebSocket
- Единая WebSocket-логика для анонимных и публичных чатов без задержек
- Редизайн кнопки «Раскрыться» по дизайну из Figma, обновление `ChatHeader`
- Загрузка и мгновенный показ аватара в настройках, шапке и публичных чатах
- Документация по сбросу базы и перезапуску фронта с пересборкой

## 🌐 Видение проекта

SoftSpeak — это гибрид психологического ассистента и безопасного мессенджера. Пользователь приходит поговорить, сначала проходит короткий диалог с ботом, затем попадает в очередь и мгновенно получает собеседника, максимально близкого по эмоциональному портрету. Общение стартует анонимно, но люди сами решают, переводить ли его в открытый режим: сначала один предлагает раскрыться, второй подтверждает, и только после обоюдного согласия чат переезжает в «публичные» с отображением аватаров и никнеймов. ML-сервис, FastAPI и React связаны единым WebSocket-потоком, поэтому SoftSpeak воспринимается как живая комната поддержки, где технологии вторят человеческой эмпатии. Это не просто чат, а платформа доверенного диалога, где приватность и открытость контролируются самими участниками, а AI помогает находить тех, кто действительно услышит.

---

Если нужна подробная схема директорий или история задач — см. `PROJECT_STRUCTURE.md`, `FIXES_APPLIED.md` и `SETTINGS_FEATURE.md`.

