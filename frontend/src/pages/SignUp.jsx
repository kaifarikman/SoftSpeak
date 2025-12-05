import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { API_URL } from '../config';
import { formatHttpError } from '../utils/errorFormatter';

function SignUp() {
  const navigate = useNavigate();
  const [login, setLogin] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');


  const validateEmail = (email) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Проверка на пустые поля
    if (!login || !login.trim()) {
      setError('Пожалуйста, введите логин');
      return;
    }
    
    if (!email || !email.trim()) {
      setError('Пожалуйста, введите адрес электронной почты');
      return;
    }

    if (!validateEmail(email)) {
      setError('Пожалуйста, введите корректный адрес электронной почты');
      return;
    }
    
    if (!password || password.length < 8) {
      setError('Пароль должен быть не менее 8 символов');
      return;
    }
    
    setLoading(true);

    try {
      const requestBody = {
        nickname: login.trim(),
        email: email.trim(),
        password: password
      };
      
      console.log('Отправка запроса регистрации:', { ...requestBody, password: '***' });

      const response = await fetch(`${API_URL}/auth/email/request`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });
      
      if (!response.ok) {
        const data = await response.json();
        console.error('Ошибка регистрации:', data);
        // Используем formatHttpError для правильного форматирования ошибок
        const errorMessage = formatHttpError(response, data);
        throw new Error(errorMessage);
      }


      // Сохраняем данные для возможной повторной отправки кода
      localStorage.setItem('pending_nickname', login.trim());
      localStorage.setItem('pending_email', email.trim());
      localStorage.setItem('pending_password', password);

      navigate('/verify', { state: { login: email.trim() } });
    } catch (err) {
      console.error(err);
      setError(err.message || 'Не удалось отправить код');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="form-box">
        <h1>Регистрация</h1>
        <p className="link-text">
          Уже есть аккаунт?{" "}
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
              navigate('/signin');
            }}
          >
            Войти
          </a>
        </p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Никнейм</label>
            <input
              type="text"
              placeholder="Никнейм"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              autocomplete="off"
              required
            />
          </div>

          <div className="form-group">
            <label>Почта</label>
            <input
              type="email"
              placeholder="Адрес электронной почты"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autocomplete="off"
              required
            />
          </div>

          <div className="form-group">
            <label>Пароль</label>
            <input
              type="password"
              placeholder="Пароль"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autocomplete="off"
              minLength={8}
              required
            />
          </div>

          {error && <p className="error-text">{error}</p>}

          <button type="submit" className="btn" disabled={loading}>
            {loading ? 'Отправка...' : 'Создать аккаунт'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default SignUp;