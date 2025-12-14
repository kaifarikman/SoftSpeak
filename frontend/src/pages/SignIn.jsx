import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { API_URL } from '../config';
import { formatHttpError } from '../utils/errorFormatter';

function SignIn() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const validateEmail = (email) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  };

  const validateEmailDomain = (email) => {
    const allowedDomains = [
      'yandex.ru', 'yandex.com', 'ya.ru',
      'mail.ru', 'inbox.ru', 'list.ru', 'bk.ru',
      'gmail.com'
    ];
    const domain = email.toLowerCase().split('@')[1];
    return allowedDomains.includes(domain);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email || !email.trim()) {
      setError('Пожалуйста, введите адрес электронной почты');
      return;
    }

    if (!validateEmail(email)) {
      setError('Пожалуйста, введите корректный адрес электронной почты');
      return;
    }

    if (!validateEmailDomain(email)) {
      setError('Доступные ящики: mail.ru, yandex.ru, gmail.com');
      return;
    }

    if (!password || !password.trim()) {
      setError('Пожалуйста, введите пароль');
      return;
    }

    setLoading(true);

    try {

      localStorage.clear();

      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email,
          password: password
        })
      });

      const data = await response.json();
      
      if (!response.ok) {

        const errorMessage = formatHttpError(response, data);
        throw new Error(errorMessage);
      }


      if (data.chat_data) {
        localStorage.setItem('chat_data', JSON.stringify(data.chat_data));
        localStorage.setItem('email', data.email);
        localStorage.setItem('nickname', data.nickname);

        window.dispatchEvent(new Event('chatDataUpdated'));
      }


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
            <label>Почта</label>
            <input 
              type="text" 
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
