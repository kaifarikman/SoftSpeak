import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { API_URL } from '../config';

function SignIn() {
  const navigate = useNavigate();
  const [login, setLogin] = useState('example_user');
  const [password, setPassword] = useState('password123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Очищаем данные предыдущего пользователя перед входом
      localStorage.clear(); // Полностью очищаем весь localStorage

      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: login,
          password: password
        })
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Неверный логин или пароль');
      }

      // Сохраняем данные чата в localStorage
      if (data.chat_data) {
        localStorage.setItem('chat_data', JSON.stringify(data.chat_data));
        localStorage.setItem('username', data.username);
        // Диспатчим событие для обновления Context
        window.dispatchEvent(new Event('chatDataUpdated'));
      }

      // Небольшая задержка для синхронизации Context перед переходом
      setTimeout(() => {
        navigate('/home', { replace: true });
      }, 100);
    } catch (err) {
      console.error(err);
      setError(err.message || 'Ошибка входа');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="form-box">
        <h1>Вход</h1>
        <p className="link-text">
          Нет аккаунта? 
          <a href="#" onClick={(e) => { e.preventDefault(); navigate('/signup'); }}>Регистрация</a>
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
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default SignIn;
