import { useNavigate, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { API_URL } from '../config';

function VerifyCode() {
  const navigate = useNavigate();
  const location = useLocation();

  // достаём email, который передали из SignUp: navigate('/verify', { state: { email } })
  const initialEmail = location.state?.login || localStorage.getItem('pending_email') || '';
  const [login, setEmail] = useState(initialEmail);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // если email появился из state — запомним его, чтобы пережить refresh
  useEffect(() => {
    if (login) localStorage.setItem('pending_login', login);
  }, [login]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      // Сохраняем login перед очисткой
      const currentLogin = login;
      
      // Очищаем данные предыдущего пользователя перед подтверждением регистрации
      localStorage.clear(); // Полностью очищаем весь localStorage

      const response = await fetch(`${API_URL}/auth/email/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: currentLogin, code: code }), // <-- backend ждёт именно это
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Неверный или просроченный код');
      }

      // Сохраняем данные чата в localStorage
      if (data.chat_data) {
        localStorage.setItem('chat_data', JSON.stringify(data.chat_data));
        localStorage.setItem('username', currentLogin);
        // Диспатчим событие для обновления Context
        window.dispatchEvent(new Event('chatDataUpdated'));
      }

      // Небольшая задержка для синхронизации Context перед переходом
      setTimeout(() => {
        navigate('/home', { replace: true });
      }, 100);
    } catch (err) {
      setError(err.message || 'Ошибка при подтверждении');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      // Для повторной отправки нужны username, email и password
      // Но у нас нет email и password в этом компоненте
      // Поэтому просто показываем сообщение, что нужно вернуться к регистрации
      setError('Для повторной отправки кода вернитесь к регистрации');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!login) {
    return (
      <div className="container">
        <div className="form-box">
          <p>Ошибка: e-mail не найден. Вернитесь к регистрации.</p>
          <button className="btn" onClick={() => navigate('/signup')}>Назад</button>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="form-box">
        <h1>Подтверждение</h1>

        <p className="subtitle" style={{ marginTop: 20 }}>
          На <b>{login}</b> отправлен код подтверждения.
        </p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Код подтверждения</label>
            <input
              type="text"
              placeholder="Введите код"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
            />
          </div>

          {error && <p className="error-text">{error}</p>}

          <p className="link-text" style={{ textAlign: 'left', marginTop: 10 }}>
            Не пришло письмо? <a href="#" onClick={handleResend}>Отправить код ещё раз</a>
          </p>

          <button type="submit" className="btn" disabled={loading}>
            {loading ? 'Проверяем…' : 'Отправить'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default VerifyCode;