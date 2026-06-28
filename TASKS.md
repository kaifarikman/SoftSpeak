# SoftSpeak — Техническая документация по открытым задачам

> Все три задачи независимы, можно брать в любом порядке.
> Стек: React 18 + FastAPI + SQLAlchemy 2.0 + asyncpg + PostgreSQL 16.

---

## Задача 1 — Теги интересов в анкете

### Что нужно сделать
После прохождения анкеты пользователь выбирает до 5 тегов интересов.
Теги учитываются при матчинге — если у двух пользователей есть общие теги, их similarity score вырастает.

---

### Шаг 1 — Бэкенд: модель и миграция

**Файл:** `backend/src/db/models.py`

Добавить в конец файла две модели:

```python
class InterestTag(Base):
    __tablename__ = "interest_tags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    emoji: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    users: Mapped[list["UserInterestTag"]] = relationship(back_populates="tag")


class UserInterestTag(Base):
    __tablename__ = "user_interest_tags"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("interest_tags.id", ondelete="CASCADE"), primary_key=True
    )
    user: Mapped["User"] = relationship(back_populates="interest_tags")
    tag: Mapped["InterestTag"] = relationship(back_populates="users")
```

В модель `User` добавить:
```python
interest_tags: Mapped[list["UserInterestTag"]] = relationship(
    back_populates="user", cascade="all, delete-orphan"
)
```

**Файл:** `backend/src/app/migrations/versions/0005_interest_tags.py`

```python
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interest_tags",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("emoji", sa.String(8), nullable=False, server_default=""),
    )
    op.create_table(
        "user_interest_tags",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("interest_tags.id", ondelete="CASCADE"), primary_key=True),
    )
    # Seed дефолтные теги
    op.execute("""
        INSERT INTO interest_tags (name, emoji) VALUES
        ('Психология', '🧠'),
        ('Спорт', '⚽'),
        ('Кино', '🎬'),
        ('Музыка', '🎵'),
        ('Технологии', '💻'),
        ('Путешествия', '✈️'),
        ('Книги', '📚'),
        ('Игры', '🎮')
    """)


def downgrade() -> None:
    op.drop_table("user_interest_tags")
    op.drop_table("interest_tags")
```

---

### Шаг 2 — Бэкенд: эндпоинты

**Новый файл:** `backend/src/api/tags.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from src.db.database import get_db
from src.db.models import InterestTag, UserInterestTag, User

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/")
async def get_all_tags(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(InterestTag).order_by(InterestTag.id))
    tags = result.scalars().all()
    return [{"id": t.id, "name": t.name, "emoji": t.emoji} for t in tags]


@router.post("/user/{email}")
async def set_user_tags(email: str, tag_ids: list[int], session: AsyncSession = Depends(get_db)):
    if len(tag_ids) > 5:
        raise HTTPException(status_code=400, detail="Максимум 5 тегов")

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    await session.execute(
        delete(UserInterestTag).where(UserInterestTag.user_id == user.id)
    )
    for tag_id in tag_ids:
        session.add(UserInterestTag(user_id=user.id, tag_id=tag_id))

    await session.commit()
    return {"ok": True}


@router.get("/user/{email}")
async def get_user_tags(email: str, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    result = await session.execute(
        select(InterestTag)
        .join(UserInterestTag, UserInterestTag.tag_id == InterestTag.id)
        .where(UserInterestTag.user_id == user.id)
    )
    tags = result.scalars().all()
    return [{"id": t.id, "name": t.name, "emoji": t.emoji} for t in tags]
```

**Файл:** `backend/src/main.py` — добавить роутер:
```python
from src.api.tags import router as tags_router
app.include_router(tags_router)
```

---

### Шаг 3 — ML: учитывать теги при матчинге

**Файл:** `backend/src/db/crud/matchmaking.py`

В функции поиска матча, после вычисления cosine similarity, добавить бонус за общие теги.
Найти место где вызывается `find_best_match` и передать туда теги текущего пользователя.

```python
# Получить теги пользователя
from sqlalchemy import select
from src.db.models import UserInterestTag

async def get_user_tag_ids(session, user_id: int) -> set[int]:
    result = await session.execute(
        select(UserInterestTag.tag_id).where(UserInterestTag.user_id == user_id)
    )
    return set(result.scalars().all())
```

**Файл:** `backend/src/services/vector_utils.py` или где живёт `find_best_match` — добавить параметр `user_tags` и `candidate_tags`:

```python
TAG_BONUS = 0.15  # бонус если есть хотя бы 1 общий тег

def apply_tag_bonus(score: float, user_tags: set[int], candidate_tags: set[int]) -> float:
    if user_tags & candidate_tags:  # пересечение множеств
        return min(1.0, score + TAG_BONUS)
    return score
```

---

### Шаг 4 — Фронтенд: шаг выбора тегов в Survey

**Файл:** `frontend/src/components/messenger/Survey.jsx`

После того как `isCompleted` становится `true` (строка 78), вместо вызова `onComplete()` сразу — показывать локальный шаг выбора тегов:

```jsx
// Добавить стейт
const [showTagStep, setShowTagStep] = useState(false);
const [selectedTags, setSelectedTags] = useState([]);
const [tags, setTags] = useState([]);
const [tagsLoading, setTagsLoading] = useState(false);

// Загрузить теги когда опрос завершён
useEffect(() => {
  if (isCompleted) {
    fetch('/api/tags/')
      .then(r => r.json())
      .then(data => { setTags(data); setShowTagStep(true); });
  }
}, [isCompleted]);

const toggleTag = (id) => {
  setSelectedTags(prev =>
    prev.includes(id)
      ? prev.filter(t => t !== id)
      : prev.length < 5 ? [...prev, id] : prev
  );
};

const submitTags = async () => {
  const email = localStorage.getItem('email');
  setTagsLoading(true);
  await fetch(`/api/tags/user/${email}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(selectedTags),
  });
  if (onComplete) onComplete();
};
```

JSX для шага тегов (рендерить вместо "Опрос завершен" когда `showTagStep`):

```jsx
if (showTagStep) {
  return (
    <div className="chat-area">
      <div className="tag-step">
        <h2>Выберите интересы</h2>
        <p>До 5 тем — мы учтём их при поиске собеседника</p>
        <div className="tag-grid">
          {tags.map(tag => (
            <button
              key={tag.id}
              className={`tag-item ${selectedTags.includes(tag.id) ? 'tag-item--selected' : ''}`}
              onClick={() => toggleTag(tag.id)}
            >
              <span>{tag.emoji}</span> {tag.name}
            </button>
          ))}
        </div>
        <button
          className="btn"
          onClick={submitTags}
          disabled={tagsLoading}
        >
          {tagsLoading ? 'Сохраняем...' : 'Продолжить →'}
        </button>
      </div>
    </div>
  );
}
```

**CSS добавить в** `frontend/src/css/components/` — новый файл `TagStep.css`:

```css
.tag-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 40px 32px;
  text-align: center;
  gap: 24px;
}

.tag-step h2 {
  font-family: 'Syne', sans-serif;
  font-size: 24px;
  font-weight: 700;
  color: #F1F0FF;
}

.tag-step p {
  color: #6B7A99;
  font-size: 15px;
}

.tag-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  max-width: 480px;
}

.tag-item {
  padding: 10px 20px;
  border-radius: 100px;
  border: 1px solid rgba(255,255,255,.1);
  background: rgba(255,255,255,.04);
  color: #94A3B8;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all .2s;
  font-family: 'Manrope', sans-serif;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tag-item:hover {
  border-color: rgba(124,58,237,.3);
  color: #C4B5FD;
}

.tag-item--selected {
  background: rgba(124,58,237,.18);
  border-color: rgba(124,58,237,.5);
  color: #E9D5FF;
}
```

---

## Задача 2 — Карточка совместимости после раскрытия

### Что нужно сделать
После того как оба пользователя нажали "Раскрыться", показать модальное окно с процентом совместимости и топ-совпадениями из анкеты.

---

### Шаг 1 — Бэкенд: сохранить similarity score в БД

**Файл:** `backend/src/db/models.py` — добавить поле в `AnonymousChat`:

```python
similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
```

**Файл:** `backend/src/app/migrations/versions/0006_anon_chat_score.py`:

```python
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"

def upgrade() -> None:
    op.add_column("anonymous_chats", sa.Column("similarity_score", sa.Float(), nullable=True))

def downgrade() -> None:
    op.drop_column("anonymous_chats", "similarity_score")
```

В момент создания матча (`backend/src/db/crud/matchmaking.py`) найти место где создаётся `AnonymousChat` и передать туда посчитанный score:

```python
# Найти создание AnonymousChat и добавить поле:
anon_chat = AnonymousChat(
    user1_id=...,
    user2_id=...,
    similarity_score=best_match["score"],  # ← добавить
    ...
)
```

---

### Шаг 2 — Бэкенд: эндпоинт совместимости

**Файл:** `backend/src/api/matchmaking.py` — добавить эндпоинт:

```python
@router.get("/chat/{chat_id}/compatibility")
async def get_compatibility(
    chat_id: int,
    email: str,
    session: AsyncSession = Depends(get_db)
):
    # Загрузить чат
    result = await session.execute(
        select(AnonymousChat).where(AnonymousChat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404)

    score = chat.similarity_score or 0.0

    # Найти общие теги
    from src.db.models import UserInterestTag, InterestTag
    tags1 = set((await session.execute(
        select(UserInterestTag.tag_id).where(UserInterestTag.user_id == chat.user1_id)
    )).scalars().all())
    tags2 = set((await session.execute(
        select(UserInterestTag.tag_id).where(UserInterestTag.user_id == chat.user2_id)
    )).scalars().all())
    common_tag_ids = tags1 & tags2

    common_tags = []
    if common_tag_ids:
        result = await session.execute(
            select(InterestTag).where(InterestTag.id.in_(common_tag_ids))
        )
        common_tags = [{"name": t.name, "emoji": t.emoji} for t in result.scalars().all()]

    return {
        "score": round(score * 100),   # 0.87 → 87
        "common_tags": common_tags,
    }
```

---

### Шаг 3 — Фронтенд: компонент CompatibilityModal

**Новый файл:** `frontend/src/components/messenger/CompatibilityModal.jsx`

```jsx
import { useEffect, useState } from 'react';
import { API_URL } from '../../config';
import { apiFetch } from '../../utils/apiHelper';
import '../../css/components/CompatibilityModal.css';

function CompatibilityModal({ chatId, email, onClose }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    apiFetch(`${API_URL}/matchmaking/chat/${chatId}/compatibility?email=${email}`)
      .then(r => r.json())
      .then(setData)
      .catch(() => {});
  }, [chatId, email]);

  if (!data) return null;

  return (
    <div className="compat-backdrop" onClick={onClose}>
      <div className="compat-modal" onClick={e => e.stopPropagation()}>
        <div className="compat-score">
          <span className="compat-percent">{data.score}%</span>
          <span className="compat-label">совместимость</span>
        </div>

        {data.common_tags.length > 0 && (
          <div className="compat-tags">
            <p className="compat-section-title">Общие интересы</p>
            <div className="compat-tag-list">
              {data.common_tags.map(tag => (
                <span key={tag.name} className="compat-tag">
                  {tag.emoji} {tag.name}
                </span>
              ))}
            </div>
          </div>
        )}

        <button className="compat-close" onClick={onClose}>
          Продолжить общение →
        </button>
      </div>
    </div>
  );
}

export default CompatibilityModal;
```

**Новый файл:** `frontend/src/css/components/CompatibilityModal.css`

```css
.compat-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.7);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  animation: fade-in .25s ease;
}

.compat-modal {
  background: #0d0d1b;
  border: 1px solid rgba(124,58,237,.3);
  border-radius: 24px;
  padding: 48px 40px;
  text-align: center;
  max-width: 380px;
  width: 90%;
  box-shadow: 0 0 80px rgba(124,58,237,.15), 0 32px 64px rgba(0,0,0,.5);
  animation: scale-in .3s cubic-bezier(.16,1,.3,1);
  position: relative;
}

.compat-modal::before {
  content: '';
  position: absolute;
  top: 0; left: 10%; right: 10%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(124,58,237,.6), rgba(34,211,238,.3), transparent);
}

.compat-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 32px;
}

.compat-percent {
  font-family: 'Syne', sans-serif;
  font-size: 80px;
  font-weight: 800;
  line-height: 1;
  background: linear-gradient(130deg, #A855F7, #22D3EE);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -3px;
}

.compat-label {
  font-size: 16px;
  color: #6B7A99;
  margin-top: 6px;
  letter-spacing: .05em;
  text-transform: uppercase;
  font-size: 12px;
  font-weight: 600;
}

.compat-section-title {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: #6B7A99;
  margin-bottom: 12px;
}

.compat-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-bottom: 32px;
}

.compat-tag {
  padding: 6px 14px;
  border-radius: 100px;
  background: rgba(124,58,237,.12);
  border: 1px solid rgba(124,58,237,.25);
  color: #C4B5FD;
  font-size: 13px;
  font-weight: 500;
}

.compat-close {
  width: 100%;
  padding: 14px;
  background: #7C3AED;
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  font-family: 'Manrope', sans-serif;
  cursor: pointer;
  transition: background .2s, transform .2s;
}

.compat-close:hover {
  background: #6D28D9;
  transform: translateY(-1px);
}

@keyframes fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}

@keyframes scale-in {
  from { opacity: 0; transform: scale(.92); }
  to   { opacity: 1; transform: scale(1); }
}
```

---

### Шаг 4 — Подключить модалку в ChatArea

**Файл:** `frontend/src/components/messenger/ChatArea.jsx`

```jsx
// Добавить импорт
import CompatibilityModal from './CompatibilityModal';

// Добавить стейт
const [showCompatibility, setShowCompatibility] = useState(false);

// Найти строку 178 — data.both_revealed:
} else if (data.type === 'chat_revealed') {
  if (data.both_revealed && onChatRevealed) {
    setShowCompatibility(true);   // ← добавить эту строку
    onChatRevealed(formattedChat);
  }
}

// В JSX перед закрывающим </div> добавить:
{showCompatibility && (
  <CompatibilityModal
    chatId={selectedChat?.id}
    email={email}
    onClose={() => setShowCompatibility(false)}
  />
)}
```

---

## Задача 3 — Модалка причины завершения чата

### Что нужно сделать
При попытке закрыть анонимный чат показывать модальное окно с вопросом "почему завершаете?". Ответ сохраняется в БД для аналитики.

---

### Шаг 1 — Бэкенд: поле close_reason в AnonymousChat

**Файл:** `backend/src/db/models.py` — добавить поле в `AnonymousChat`:

```python
close_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
```

**Файл:** `backend/src/app/migrations/versions/0007_anon_chat_close_reason.py`:

```python
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"

def upgrade() -> None:
    op.add_column("anonymous_chats", sa.Column("close_reason", sa.String(64), nullable=True))

def downgrade() -> None:
    op.drop_column("anonymous_chats", "close_reason")
```

**Файл:** `backend/src/api/matchmaking.py` — добавить эндпоинт:

```python
@router.post("/chat/{chat_id}/close")
async def close_chat(
    chat_id: int,
    email: str,
    reason: str,
    session: AsyncSession = Depends(get_db)
):
    result = await session.execute(
        select(AnonymousChat).where(AnonymousChat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404)

    chat.close_reason = reason
    chat.is_active = False
    await session.commit()
    return {"ok": True}
```

---

### Шаг 2 — Фронтенд: компонент CloseReasonModal

**Новый файл:** `frontend/src/components/messenger/CloseReasonModal.jsx`

```jsx
import '../../css/components/CloseReasonModal.css';

const REASONS = [
  { id: 'connected',  label: 'Нашли общий язык', emoji: '🤝' },
  { id: 'boring',     label: 'Неинтересно',       emoji: '😐' },
  { id: 'technical',  label: 'Технические проблемы', emoji: '⚙️' },
  { id: 'other',      label: 'Другое',             emoji: '💬' },
];

function CloseReasonModal({ onConfirm, onCancel }) {
  return (
    <div className="close-reason-backdrop" onClick={onCancel}>
      <div className="close-reason-modal" onClick={e => e.stopPropagation()}>
        <h3>Почему завершаете чат?</h3>
        <p>Это поможет нам улучшить сервис</p>
        <div className="close-reason-list">
          {REASONS.map(r => (
            <button
              key={r.id}
              className="close-reason-item"
              onClick={() => onConfirm(r.id)}
            >
              <span className="close-reason-emoji">{r.emoji}</span>
              {r.label}
            </button>
          ))}
        </div>
        <button className="close-reason-cancel" onClick={onCancel}>
          Отмена
        </button>
      </div>
    </div>
  );
}

export default CloseReasonModal;
```

**Новый файл:** `frontend/src/css/components/CloseReasonModal.css`

```css
.close-reason-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.65);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  animation: fade-in .2s ease;
}

.close-reason-modal {
  background: #0d0d1b;
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 20px;
  padding: 36px 32px;
  max-width: 360px;
  width: 90%;
  box-shadow: 0 24px 64px rgba(0,0,0,.5);
  animation: scale-in .25s cubic-bezier(.16,1,.3,1);
}

.close-reason-modal h3 {
  font-family: 'Syne', sans-serif;
  font-size: 20px;
  font-weight: 700;
  color: #F1F0FF;
  margin-bottom: 6px;
}

.close-reason-modal p {
  font-size: 13px;
  color: #6B7A99;
  margin-bottom: 24px;
}

.close-reason-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.close-reason-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 16px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,.07);
  background: rgba(255,255,255,.03);
  color: #CBD5E1;
  font-size: 14px;
  font-weight: 500;
  font-family: 'Manrope', sans-serif;
  cursor: pointer;
  text-align: left;
  transition: background .15s, border-color .15s;
}

.close-reason-item:hover {
  background: rgba(124,58,237,.1);
  border-color: rgba(124,58,237,.25);
  color: #F1F0FF;
}

.close-reason-emoji {
  font-size: 18px;
  flex-shrink: 0;
}

.close-reason-cancel {
  width: 100%;
  padding: 12px;
  background: transparent;
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 10px;
  color: #6B7A99;
  font-size: 14px;
  font-family: 'Manrope', sans-serif;
  cursor: pointer;
  transition: all .15s;
}

.close-reason-cancel:hover {
  background: rgba(255,255,255,.04);
  color: #94A3B8;
}

@keyframes fade-in  { from { opacity: 0; } to { opacity: 1; } }
@keyframes scale-in { from { opacity: 0; transform: scale(.94); } to { opacity: 1; transform: scale(1); } }
```

---

### Шаг 3 — Подключить модалку в ChatArea

**Файл:** `frontend/src/components/messenger/ChatArea.jsx`

```jsx
// Добавить импорт
import CloseReasonModal from './CloseReasonModal';

// Добавить стейт
const [showCloseReason, setShowCloseReason] = useState(false);

// Найти кнопку/логику закрытия чата.
// Вместо прямого вызова closeChat() — сначала показать модалку:
const handleCloseChat = () => {
  if (activeSection === 'anon') {
    setShowCloseReason(true);
  } else {
    closeChat();  // для не-анонимных чатов — закрывать сразу
  }
};

const handleCloseWithReason = async (reason) => {
  setShowCloseReason(false);
  const email = localStorage.getItem('email');
  await apiFetch(`${API_URL}/matchmaking/chat/${selectedChat.id}/close?email=${email}&reason=${reason}`, {
    method: 'POST',
  });
  closeChat();  // вызов существующей функции закрытия
};

// В JSX добавить:
{showCloseReason && (
  <CloseReasonModal
    onConfirm={handleCloseWithReason}
    onCancel={() => setShowCloseReason(false)}
  />
)}
```

---

## Порядок реализации

Рекомендую такой порядок если делать последовательно:

1. **Задача 3** (CloseReasonModal) — только фронт + 1 поле в БД, самая простая
2. **Задача 1** (Теги) — бэкенд + ML + фронт, но всё независимо и хорошо изолировано
3. **Задача 2** (Совместимость) — зависит от тегов (нужны данные для `common_tags`), делать после задачи 1

## После каждой задачи

```bash
# Пересобрать и перезапустить
docker compose build backend && docker compose up -d backend

# Для фронтенда
docker compose build frontend && docker compose up -d frontend

# Проверить миграции (выполнятся автоматически при старте бэкенда)
docker compose logs backend | grep -i "alembic\|migrat"
```
