import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import '../css/Landing.css';

function Landing() {
  const navigate = useNavigate();

  useEffect(() => {
    const email = localStorage.getItem('email');
    if (email) {
      navigate('/home');
    }
  }, [navigate]);

  return (
    <div className="landing-container">
      <div className="landing-orb landing-orb-1" />
      <div className="landing-orb landing-orb-2" />
      <div className="landing-orb landing-orb-3" />

      <div className="landing-content">
        <div className="logo-section">
          <div className="logo-eyebrow">
            <span className="logo-eyebrow-dot" />
            Анонимный чат нового поколения
          </div>
          <h1 className="logo-title">
            <span className="logo-soft">Soft</span>
            <span className="logo-speak">Speak</span>
          </h1>
          <p className="logo-subtitle">
            Умные алгоритмы подбирают собеседника по психологической совместимости — общайтесь анонимно и раскрывайтесь, когда готовы
          </p>
        </div>

        <div className="features-section">
          <div className="feature-card">
            <div className="feature-number">01 — Интеллект</div>
            <span className="feature-icon">🧠</span>
            <h3>Умный матчинг</h3>
            <p>ML-алгоритмы подбирают собеседников на основе психологической совместимости</p>
          </div>

          <div className="feature-card">
            <div className="feature-number">02 — Приватность</div>
            <span className="feature-icon">🎭</span>
            <h3>Анонимность</h3>
            <p>Начните общение анонимно и раскройтесь, когда будете готовы</p>
          </div>

          <div className="feature-card">
            <div className="feature-number">03 — Скорость</div>
            <span className="feature-icon">⚡</span>
            <h3>Реальное время</h3>
            <p>Мгновенный обмен сообщениями через WebSocket-соединение</p>
          </div>
        </div>

        <div className="cta-section">
          <button className="cta-button primary" onClick={() => navigate('/signup')}>
            Начать общение
          </button>
          <button className="cta-button secondary" onClick={() => navigate('/signin')}>
            Войти
          </button>
        </div>
      </div>
    </div>
  );
}

export default Landing;
