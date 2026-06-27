import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { API_URL } from '../config';
import { formatHttpError } from '../utils/errorFormatter';
import { clearAuthStorage, setAccessToken } from '../utils/apiHelper';

function SignIn() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [allowedDomains, setAllowedDomains] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/auth/email/domains`)
      .then((response) => (response.ok ? response.json() : null))
      .then((domains) => {
        if (Array.isArray(domains)) {
          setAllowedDomains(domains);
        }
      })
      .catch(() => {});
  }, []);

  const validateEmail = (email) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  };

  const validateEmailDomain = (email) => {
    if (!allowedDomains) {
      return true;
    }
    const domain = email.toLowerCase().split('@')[1];
    return allowedDomains.includes(domain);
  };

  const getDomainError = () => {
    if (!allowedDomains || allowedDomains.length === 0) {
      return 'Доступные ящики: mail.ru, yandex.ru, gmail.com';
    }
    return `Доступные ящики: ${allowedDomains.join(', ')}`;
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
      setError(getDomainError());
      return;
    }

    if (!password || !password.trim()) {
      setError('Пожалуйста, введите пароль');
      return;
    }

    setLoading(true);

    try {

      clearAuthStorage();

      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        credentials: 'include',
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


      setAccessToken(data.access_token);

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
