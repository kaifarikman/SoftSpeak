import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { API_URL } from '../config';

function SignUp() {
  const navigate = useNavigate();
  const [login, setLogin] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Валидация email
  const validateEmail = (email) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Проверяем формат email
    if (!validateEmail(email)) {
      setError('Пожалуйста, введите корректный адрес электронной почты');
      return;
    }
    
    setLoading(true);

    try {
      // Отправляем только email
      const response = await fetch(`${API_URL}/auth/email/request`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: login,
          email: email,
          password: password
        })
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail?.message || 'Ошибка регистрации');
      }

      // Всё ок — переход на страницу ввода кода
      navigate('/verify', { state: { login } });
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
            <label>Логин</label>
            <input
              type="text"
              placeholder="Логин"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
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