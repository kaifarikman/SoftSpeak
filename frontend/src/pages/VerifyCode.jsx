import { useNavigate, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { API_URL } from '../config';

function VerifyCode() {
  const navigate = useNavigate();
  const location = useLocation();


  const initialEmail = location.state?.login || localStorage.getItem('pending_email') || '';
  const [login, setEmail] = useState(initialEmail);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');


  useEffect(() => {
    if (login) localStorage.setItem('pending_login', login);
  }, [login]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {

      const currentLogin = login;
      

      localStorage.clear();

      const response = await fetch(`${API_URL}/auth/email/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nickname: currentLogin, code: code }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Неверный или просроченный код');
      }


      if (data.chat_data) {
        localStorage.setItem('chat_data', JSON.stringify(data.chat_data));
        // Сохраняем nickname, email будет сохранен после подтверждения
        localStorage.setItem('nickname', currentLogin);

        window.dispatchEvent(new Event('chatDataUpdated'));
      }


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