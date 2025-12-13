# Frontend - Подробная инструкция

## 📚 Содержание

1. [Что такое Frontend?](#что-такое-frontend)
2. [Технологии и инструменты](#технологии-и-инструменты)
3. [Структура проекта](#структура-проекта)
4. [React - основы](#react---основы)
5. [Компоненты](#компоненты)
6. [Роутинг](#роутинг)
7. [Состояние приложения](#состояние-приложения)
8. [Работа с API](#работа-с-api)
9. [WebSocket соединения](#websocket-соединения)
10. [Стилизация (CSS)](#стилизация-css)
11. [Сборка и деплой](#сборка-и-деплой)
12. [Типичные проблемы и решения](#типичные-проблемы-и-решения)

---

## Что такое Frontend?

**Frontend** (фронтенд) - это "передняя часть" веб-приложения, которую видит и с которой взаимодействует пользователь. Это все, что происходит в браузере.

**Аналогия:** Если Backend - это кухня ресторана, то Frontend - это зал, где сидят посетители, видят меню и делают заказы.

### Что делает Frontend в нашем проекте?

1. **Отображает интерфейс** - показывает страницы, кнопки, формы
2. **Обрабатывает действия пользователя** - клики, ввод текста, отправка форм
3. **Общается с Backend** - отправляет запросы и получает данные
4. **Обеспечивает real-time коммуникацию** - через WebSocket получает сообщения в реальном времени
5. **Хранит данные локально** - сохраняет токены, настройки в браузере

### Простой пример работы Frontend

**Сценарий:** Пользователь хочет зарегистрироваться

1. **Пользователь** видит форму регистрации (Frontend отображает)
2. **Пользователь** вводит email и пароль (Frontend получает данные)
3. **Пользователь** нажимает "Зарегистрироваться" (Frontend обрабатывает клик)
4. **Frontend** отправляет данные на Backend через API
5. **Backend** отвечает: "Код отправлен на email"
6. **Frontend** показывает сообщение: "Проверьте почту"

---

## Технологии и инструменты

### React 18

**React** - это библиотека JavaScript для создания пользовательских интерфейсов. Это как конструктор для веб-страниц.

**Что такое библиотека?** Это набор готовых инструментов, которые упрощают разработку. Вместо того чтобы писать весь код с нуля, мы используем готовые функции React.

**Основные концепции React:**

#### 1. Компоненты

**Компонент** - это переиспользуемый кусок интерфейса. Это как блок конструктора LEGO.

**Пример простого компонента:**
```javascript
function Button() {
  return <button>Нажми меня</button>;
}
```

Это компонент кнопки. Его можно использовать много раз:
```javascript
<Button />
<Button />
<Button />
```

#### 2. Props (Свойства)

**Props** - это данные, которые передаются в компонент. Это как параметры функции.

**Пример:**
```javascript
function Button({ text, onClick }) {
  return <button onClick={onClick}>{text}</button>;
}

// Использование:
<Button text="Отправить" onClick={handleClick} />
```

#### 3. State (Состояние)

**State** - это данные компонента, которые могут изменяться. Когда state изменяется, компонент перерисовывается.

**Пример:**
```javascript
function Counter() {
  const [count, setCount] = useState(0);  // count = 0
  
  return (
    <div>
      <p>Счет: {count}</p>
      <button onClick={() => setCount(count + 1)}>
        Увеличить
      </button>
    </div>
  );
}
```

Когда пользователь нажимает кнопку, `count` увеличивается, и компонент перерисовывается с новым значением.

#### 4. Hooks (Хуки)

**Hooks** - это функции, которые позволяют использовать возможности React в компонентах.

**Основные хуки:**

- **useState** - для состояния
```javascript
const [value, setValue] = useState(0);
```

- **useEffect** - для побочных эффектов (загрузка данных, подписки)
```javascript
useEffect(() => {
  // Код выполняется при монтировании компонента
  fetchData();
  
  return () => {
    // Код выполняется при размонтировании (очистка)
    cleanup();
  };
}, [dependencies]);  // Зависимости - когда перезапускать
```

- **useRef** - для ссылок на DOM элементы
```javascript
const inputRef = useRef(null);
<input ref={inputRef} />
```

- **useCallback** - для мемоизации функций
```javascript
const handleClick = useCallback(() => {
  // Функция не пересоздается при каждом рендере
}, [dependencies]);
```

### Vite

**Vite** - это инструмент для сборки и разработки. Это как конвейер на заводе, который собирает готовый продукт из деталей.

**Что делает Vite:**
1. **Разработка** - запускает сервер разработки с горячей перезагрузкой (изменения видны сразу)
2. **Сборка** - компилирует код в оптимизированные файлы для продакшена
3. **Оптимизация** - минифицирует код, объединяет файлы

**Преимущества Vite:**
- Очень быстрый запуск
- Мгновенная горячая перезагрузка
- Оптимизированная сборка

### React Router

**React Router** - это библиотека для навигации между страницами в одностраничном приложении (SPA).

**Что такое SPA?** Single Page Application - приложение, которое загружается один раз, а затем JavaScript меняет содержимое страницы без перезагрузки.

**Как это работает:**
```javascript
<Routes>
  <Route path="/" element={<Landing />} />
  <Route path="/signup" element={<SignUp />} />
  <Route path="/home" element={<Messenger />} />
</Routes>
```

Когда пользователь переходит на `/signup`, React Router показывает компонент `<SignUp />` без перезагрузки страницы.

### Nginx

**Nginx** - это веб-сервер, который отдает статические файлы (HTML, CSS, JavaScript) и проксирует запросы к Backend.

**В продакшене:**
- Отдает собранные файлы Frontend
- Проксирует `/api/*` запросы к Backend
- Проксирует WebSocket соединения к Backend

---

## Структура проекта

```
frontend/
├── Dockerfile              # Инструкции для создания Docker образа
├── nginx.conf              # Конфигурация Nginx
├── package.json            # Зависимости проекта
├── vite.config.js          # Конфигурация Vite
├── index.html              # Главный HTML файл
└── src/                    # Исходный код
    ├── main.jsx            # Точка входа
    ├── App.jsx             # Главный компонент (роутинг)
    ├── config.js           # Конфигурация (API_URL)
    ├── pages/              # Страницы
    │   ├── Landing.jsx     # Лендинг
    │   ├── SignUp.jsx      # Регистрация
    │   ├── SignIn.jsx      # Вход
    │   ├── VerifyCode.jsx  # Подтверждение email
    │   ├── FirstStart.jsx  # Первый запуск (опрос)
    │   ├── Messenger.jsx   # Главный мессенджер
    │   └── Admin.jsx       # Админ-панель
    ├── components/         # Компоненты
    │   ├── messenger/      # Компоненты мессенджера
    │   │   ├── Sidebar.jsx
    │   │   ├── ChatArea.jsx
    │   │   ├── ChatList.jsx
    │   │   ├── MessageList.jsx
    │   │   ├── MessageInput.jsx
    │   │   ├── ChatHeader.jsx
    │   │   ├── SettingsContent.jsx
    │   │   ├── Survey.jsx
    │   │   └── ...
    │   ├── ErrorBoundary.jsx
    │   └── BannedOverlay.jsx
    ├── context/            # React Context
    │   └── ChatDataContext.jsx
    ├── utils/              # Утилиты
    │   ├── apiHelper.js
    │   ├── errorFormatter.js
    │   ├── errorHandler.js
    │   └── url.js
    └── css/                # Стили
        ├── App.css
        ├── Messenger.css
        └── components/
```

### Описание основных файлов

#### `main.jsx` - Точка входа

Это первый файл, который выполняется. Он:
- Рендерит главный компонент `<App />`
- Подключает стили
- Настраивает React

**Пример:**
```javascript
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './css/App.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

#### `App.jsx` - Главный компонент

Содержит роутинг (навигацию между страницами).

**Пример:**
```javascript
import { Routes, Route } from 'react-router-dom';
import Landing from './pages/Landing';
import Messenger from './pages/Messenger';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/home" element={<Messenger />} />
    </Routes>
  );
}
```

#### `pages/` - Страницы

Каждый файл - это отдельная страница приложения.

**Пример `SignUp.jsx`:**
```javascript
function SignUp() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    // Отправка данных на Backend
    const response = await fetch(`${API_URL}/auth/email/request`, {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input value={email} onChange={(e) => setEmail(e.target.value)} />
      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <button type="submit">Зарегистрироваться</button>
    </form>
  );
}
```

#### `components/` - Компоненты

Переиспользуемые компоненты интерфейса.

**Пример `Button.jsx`:**
```javascript
function Button({ text, onClick, disabled }) {
  return (
    <button onClick={onClick} disabled={disabled}>
      {text}
    </button>
  );
}
```

---

## React - основы

### Жизненный цикл компонента

**Жизненный цикл** - это этапы существования компонента от создания до удаления.

**Этапы:**
1. **Монтирование** - компонент создается и добавляется в DOM
2. **Обновление** - компонент перерисовывается при изменении props или state
3. **Размонтирование** - компонент удаляется из DOM

**useEffect для жизненного цикла:**
```javascript
useEffect(() => {
  // Код выполняется при монтировании
  
  return () => {
    // Код выполняется при размонтировании (очистка)
  };
}, []);  // Пустой массив = только при монтировании/размонтировании
```

### Условный рендеринг

**Условный рендеринг** - это отображение разных элементов в зависимости от условий.

**Пример:**
```javascript
function UserProfile({ user }) {
  if (!user) {
    return <p>Загрузка...</p>;
  }
  
  return (
    <div>
      <h1>{user.name}</h1>
      {user.isAdmin && <AdminPanel />}
    </div>
  );
}
```

### Списки и ключи

**Рендеринг списков** - отображение массива элементов.

**Пример:**
```javascript
function ChatList({ chats }) {
  return (
    <ul>
      {chats.map(chat => (
        <li key={chat.id}>{chat.name}</li>
      ))}
    </ul>
  );
}
```

**Важно:** Каждый элемент должен иметь уникальный `key` для оптимизации React.

### Обработка событий

**События** - это действия пользователя (клики, ввод текста, и т.д.).

**Пример:**
```javascript
function Button() {
  const handleClick = () => {
    console.log('Кнопка нажата!');
  };
  
  return <button onClick={handleClick}>Нажми меня</button>;
}
```

### Формы

**Формы** - это элементы для ввода данных.

**Пример:**
```javascript
function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  const handleSubmit = (e) => {
    e.preventDefault();  // Предотвращаем перезагрузку страницы
    console.log('Email:', email, 'Password:', password);
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Пароль"
      />
      <button type="submit">Войти</button>
    </form>
  );
}
```

---

## Компоненты

### Messenger.jsx - Главный мессенджер

**Что делает:** Главная страница приложения после входа. Содержит:
- Боковую панель с навигацией
- Область чата
- Список чатов
- Настройки

**Структура:**
```javascript
function Messenger() {
  const [activeSection, setActiveSection] = useState('anon');
  const [selectedChat, setSelectedChat] = useState(null);
  
  return (
    <div className="messenger-container">
      <Sidebar onSectionChange={setActiveSection} />
      <ChatArea
        selectedChat={selectedChat}
        activeSection={activeSection}
      />
    </div>
  );
}
```

### Sidebar.jsx - Боковая панель

**Что делает:** Навигация между разделами (анонимные чаты, AI чат, настройки).

**Секции:**
- `anon` - анонимные чаты
- `bot` - AI чат
- `settings` - настройки

### ChatArea.jsx - Область чата

**Что делает:** Отображает выбранный чат или настройки.

**Состояния:**
- Показывает список сообщений
- Показывает поле ввода
- Показывает заголовок чата
- Управляет WebSocket соединениями

**WebSocket соединения:**
```javascript
useEffect(() => {
  if (selectedChat) {
    const ws = new WebSocket(`ws://localhost:8000/api/matchmaking/chat/${selectedChat.id}/ws/${email}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'new_message') {
        setMessages(prev => [...prev, data.message]);
      }
    };
    
    return () => ws.close();
  }
}, [selectedChat]);
```

### MessageList.jsx - Список сообщений

**Что делает:** Отображает список сообщений в чате.

**Особенности:**
- Автоматическая прокрутка к последнему сообщению
- Разделение сообщений по датам
- Отображение статуса прочтения

**Автопрокрутка:**
```javascript
const messagesEndRef = useRef(null);

useEffect(() => {
  messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
}, [messages]);
```

### MessageInput.jsx - Поле ввода

**Что делает:** Поле для ввода и отправки сообщений.

**Функции:**
- Ввод текста
- Отправка сообщения (Enter или кнопка)
- Валидация (не отправлять пустые сообщения)

### ChatHeader.jsx - Заголовок чата

**Что делает:** Отображает информацию о чате (имя собеседника, кнопки действий).

**Действия:**
- Раскрытие чата (показать реальные никнеймы)
- Пожаловаться на пользователя
- Просмотр профиля

### SettingsContent.jsx - Настройки

**Что делает:** Отображает и редактирует настройки пользователя.

**Разделы:**
- Профиль (никнейм, био)
- Уведомления
- Аккаунт (смена пароля)

---

## Роутинг

### Что такое роутинг?

**Роутинг** - это навигация между страницами в приложении.

**В обычном веб-сайте:**
- Каждая страница - это отдельный HTML файл
- Переход = загрузка нового файла

**В SPA (Single Page Application):**
- Один HTML файл
- JavaScript меняет содержимое
- Переход = изменение компонента

### Настройка роутинга

**Файл:** `App.jsx`

```javascript
import { Routes, Route } from 'react-router-dom';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/signup" element={<SignUp />} />
      <Route path="/signin" element={<SignIn />} />
      <Route path="/verify" element={<VerifyCode />} />
      <Route path="/home" element={<Messenger />} />
      <Route path="/admin" element={<Admin />} />
    </Routes>
  );
}
```

### Навигация между страницами

**Использование `useNavigate`:**
```javascript
import { useNavigate } from 'react-router-dom';

function LoginButton() {
  const navigate = useNavigate();
  
  const handleLogin = () => {
    // Логика входа
    navigate('/home');  // Переход на страницу /home
  };
  
  return <button onClick={handleLogin}>Войти</button>;
}
```

**Использование `<Link>`:**
```javascript
import { Link } from 'react-router-dom';

function Navigation() {
  return (
    <nav>
      <Link to="/">Главная</Link>
      <Link to="/home">Мессенджер</Link>
    </nav>
  );
}
```

---

## Состояние приложения

### Что такое состояние?

**Состояние** - это данные приложения, которые могут изменяться и влиять на отображение.

**Типы состояния:**
1. **Локальное состояние** - данные одного компонента
2. **Глобальное состояние** - данные, доступные всем компонентам

### Локальное состояние (useState)

**Использование:**
```javascript
function Counter() {
  const [count, setCount] = useState(0);
  
  return (
    <div>
      <p>Счет: {count}</p>
      <button onClick={() => setCount(count + 1)}>+</button>
    </div>
  );
}
```

### Глобальное состояние (Context)

**Context** - это способ передачи данных через дерево компонентов без props.

**Создание Context:**
```javascript
// ChatDataContext.jsx
import { createContext, useContext, useState } from 'react';

const ChatDataContext = createContext();

export const ChatDataProvider = ({ children }) => {
  const [chatData, setChatData] = useState(null);
  
  return (
    <ChatDataContext.Provider value={{ chatData, setChatData }}>
      {children}
    </ChatDataContext.Provider>
  );
};

export const useChatData = () => {
  const context = useContext(ChatDataContext);
  if (!context) {
    throw new Error('useChatData must be used within ChatDataProvider');
  }
  return context;
};
```

**Использование:**
```javascript
// В любом компоненте
function MyComponent() {
  const { chatData, setChatData } = useChatData();
  
  return <div>{chatData?.user?.nickname}</div>;
}
```

### LocalStorage

**LocalStorage** - это хранилище в браузере для постоянного хранения данных.

**Использование:**
```javascript
// Сохранение
localStorage.setItem('token', 'abc123');
localStorage.setItem('user', JSON.stringify({ name: 'Иван' }));

// Чтение
const token = localStorage.getItem('token');
const user = JSON.parse(localStorage.getItem('user'));

// Удаление
localStorage.removeItem('token');
localStorage.clear();  // Очистить все
```

**Важно:** LocalStorage хранит только строки. Для объектов используйте `JSON.stringify()` и `JSON.parse()`.

---

## Работа с API

### Что такое API?

**API (Application Programming Interface)** - это интерфейс для общения между Frontend и Backend.

**Аналогия:** API - это меню в ресторане. Frontend "заказывает" данные, Backend "готовит" и возвращает.

### Fetch API

**Fetch** - это встроенный в браузер способ делать HTTP запросы.

**Простой GET запрос:**
```javascript
const response = await fetch('http://localhost:8000/api/users/123');
const data = await response.json();
console.log(data);
```

**POST запрос:**
```javascript
const response = await fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    email: 'user@mail.ru',
    password: 'password123'
  })
});

const data = await response.json();
```

**С обработкой ошибок:**
```javascript
try {
  const response = await fetch(url, options);
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  const data = await response.json();
  return data;
} catch (error) {
  console.error('Ошибка:', error);
  throw error;
}
```

### Работа с JWT токенами

**JWT токен** - это пропуск для доступа к защищенным endpoints.

**Сохранение токена:**
```javascript
const response = await fetch('/api/auth/login', { ... });
const data = await response.json();
localStorage.setItem('token', data.token);
```

**Использование токена:**
```javascript
const token = localStorage.getItem('token');

const response = await fetch('/api/protected', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

### Обработка ошибок

**Форматирование ошибок:**
```javascript
// errorFormatter.js
export function formatHttpError(response, errorData) {
  switch (response.status) {
    case 401:
      return 'Неверный email или пароль';
    case 403:
      return errorData.detail || 'Доступ запрещен';
    case 404:
      return 'Ресурс не найден';
    case 422:
      return formatApiError(errorData);
    default:
      return errorData.detail || 'Произошла ошибка';
  }
}
```

**Использование:**
```javascript
const response = await fetch(url);
if (!response.ok) {
  const errorData = await response.json();
  const errorMessage = formatHttpError(response, errorData);
  throw new Error(errorMessage);
}
```

---

## WebSocket соединения

### Что такое WebSocket?

**WebSocket** - это протокол для двусторонней связи в реальном времени. В отличие от обычного HTTP, где нужно постоянно спрашивать "есть ли новые данные?", WebSocket позволяет серверу самому отправлять данные.

**Аналогия:**
- **HTTP** - телефон, нужно звонить каждый раз
- **WebSocket** - рация, можно говорить в любой момент

### Создание WebSocket соединения

**Базовый пример:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/matchmaking/ws/user@mail.ru');

ws.onopen = () => {
  console.log('Соединение установлено');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Получено:', data);
};

ws.onerror = (error) => {
  console.error('Ошибка:', error);
};

ws.onclose = () => {
  console.log('Соединение закрыто');
};
```

### Отправка данных через WebSocket

```javascript
ws.send(JSON.stringify({
  type: 'message',
  text: 'Привет!'
}));
```

### Закрытие соединения

```javascript
ws.close();
```

### WebSocket для чатов

**Пример из проекта:**
```javascript
useEffect(() => {
  if (selectedChat) {
    const ws = new WebSocket(
      `${WS_URL}/matchmaking/chat/${selectedChat.id}/ws/${email}`
    );
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'new_message') {
        setMessages(prev => [...prev, data.message]);
      } else if (data.type === 'chat_revealed') {
        onChatRevealed(data.chat_id);
      }
    };
    
    wsRef.current = ws;
    
    return () => {
      ws.close();
    };
  }
}, [selectedChat]);
```

### Переподключение при разрыве

```javascript
const reconnectWebSocket = () => {
  if (reconnectTimeoutRef.current) {
    clearTimeout(reconnectTimeoutRef.current);
  }
  
  reconnectTimeoutRef.current = setTimeout(() => {
    connectWebSocket();
  }, 3000);  // Переподключение через 3 секунды
};

ws.onclose = () => {
  reconnectWebSocket();
};
```

---

## Стилизация (CSS)

### Что такое CSS?

**CSS (Cascading Style Sheets)** - это язык для описания внешнего вида веб-страниц.

**Аналогия:** Если HTML - это скелет (структура), то CSS - это кожа и одежда (внешний вид).

### Основы CSS

**Синтаксис:**
```css
селектор {
  свойство: значение;
}
```

**Пример:**
```css
.button {
  background-color: blue;
  color: white;
  padding: 10px;
  border-radius: 5px;
}
```

### Селекторы

**Класс:**
```css
.button { }
```

**ID:**
```css
#header { }
```

**Элемент:**
```css
button { }
```

**Вложенность:**
```css
.container .button { }
```

### Основные свойства

**Цвета:**
```css
color: #ffffff;           /* Цвет текста */
background-color: #000000; /* Цвет фона */
```

**Размеры:**
```css
width: 100px;
height: 50px;
padding: 10px;    /* Внутренние отступы */
margin: 20px;     /* Внешние отступы */
```

**Текст:**
```css
font-size: 16px;
font-weight: bold;
text-align: center;
```

**Позиционирование:**
```css
position: relative;  /* Относительное */
position: absolute;  /* Абсолютное */
position: fixed;     /* Фиксированное */
```

**Flexbox:**
```css
display: flex;
flex-direction: column;  /* Вертикально */
justify-content: center; /* По центру */
align-items: center;     /* По центру */
```

### CSS в React

**Импорт CSS:**
```javascript
import './css/App.css';
```

**Использование классов:**
```javascript
<div className="container">
  <button className="button primary">Нажми</button>
</div>
```

### Особенности стилизации в проекте

**Статичные заголовки:**
Заголовки чата и настроек не скроллятся вместе с контентом:
```css
.chat-header {
  position: relative !important;
  flex-shrink: 0 !important;
}

.message-list {
  flex: 1 !important;
  overflow-y: auto !important;
}
```

**Глобальные правила:**
```css
html, body {
  overflow: hidden !important;
  height: 100%;
}
```

**Исключение для админки:**
```css
html.admin-page,
body.admin-page {
  overflow: auto !important;
  height: auto !important;
}
```

---

## Сборка и деплой

### Разработка

**Запуск сервера разработки:**
```bash
npm run dev
```

Это запустит Vite dev server на `http://localhost:5173` с горячей перезагрузкой.

### Сборка для продакшена

**Сборка:**
```bash
npm run build
```

Это создаст папку `dist/` с оптимизированными файлами:
- Минифицированный JavaScript
- Оптимизированный CSS
- Оптимизированные изображения

### Docker сборка

**Dockerfile:**
```dockerfile
# Этап 1: Сборка
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Этап 2: Продакшен
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Сборка образа:**
```bash
docker build -t softspeak-frontend .
```

**Запуск:**
```bash
docker run -p 3000:80 softspeak-frontend
```

### Nginx конфигурация

**nginx.conf:**
```nginx
server {
    listen 80;
    
    # Статические файлы
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
    
    # Проксирование API
    location /api/ {
        proxy_pass http://backend:8000/;
    }
    
    # Проксирование WebSocket
    location /api/ws/ {
        proxy_pass http://backend:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Типичные проблемы и решения

### Проблема: "CORS error"

**Причина:** Backend не разрешает запросы с этого домена.

**Решение:**
Проверьте настройки CORS в Backend:
```python
CORS_ORIGINS=https://yourdomain.com
```

### Проблема: "WebSocket connection failed"

**Причина:** Проблемы с проксированием или URL.

**Решение:**
1. Проверьте `WS_URL` в `config.js`
2. Проверьте настройки Nginx для WebSocket
3. Убедитесь, что Backend запущен

### Проблема: "Token expired"

**Причина:** JWT токен истек.

**Решение:**
```javascript
if (response.status === 401) {
  localStorage.removeItem('token');
  navigate('/signin');
}
```

### Проблема: "State not updating"

**Причина:** Неправильное использование state.

**Решение:**
Используйте функциональное обновление:
```javascript
// Неправильно
setCount(count + 1);

// Правильно (если count может измениться)
setCount(prev => prev + 1);
```

### Проблема: "Memory leak"

**Причина:** Не очищаются подписки или таймеры.

**Решение:**
Очищайте в `useEffect`:
```javascript
useEffect(() => {
  const timer = setInterval(() => {
    // Код
  }, 1000);
  
  return () => {
    clearInterval(timer);  // Очистка
  };
}, []);
```

---

## Заключение

Этот документ покрывает основные аспекты Frontend микросервиса. Для более детальной информации смотрите код и комментарии в файлах проекта.

**Полезные ссылки:**
- React документация: https://react.dev/
- Vite документация: https://vitejs.dev/
- React Router документация: https://reactrouter.com/

