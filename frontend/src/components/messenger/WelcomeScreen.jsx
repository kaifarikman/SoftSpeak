import '../../css/components/WelcomeScreen.css';

function WelcomeScreen({ username }) {
  return (
    <div className="welcome-screen">
      <div className="welcome-content">
        <div className="welcome-logo">
          <h1 className="welcome-title">
            <span className="logo-soft">Soft</span>
            <span className="logo-speak">Speak</span>
          </h1>
          <p className="welcome-subtitle">Платформа доверенного диалога</p>
        </div>

        {username && (
          <div className="welcome-greeting">
            <p className="greeting-text">Добро пожаловать, <span className="username-highlight">{username}</span>!</p>
          </div>
        )}

        <div className="welcome-features">
          <div className="feature-item">
            <div className="feature-emoji">🤖</div>
            <h3>AI Чат-бот</h3>
            <p>Умный ассистент для психологической поддержки</p>
          </div>

          <div className="feature-item">
            <div className="feature-emoji">🎭</div>
            <h3>Анонимные чаты</h3>
            <p>Найдите собеседника и общайтесь инкогнито</p>
          </div>

          <div className="feature-item">
            <div className="feature-emoji">👥</div>
            <h3>Публичные чаты</h3>
            <p>Раскройте свою личность и продолжите общение</p>
          </div>

          <div className="feature-item">
            <div className="feature-emoji">⚙️</div>
            <h3>Настройки</h3>
            <p>Персонализируйте свой профиль и предпочтения</p>
          </div>
        </div>

        <div className="welcome-instruction">
          <p className="instruction-text">
            👈 Выберите раздел в меню слева, чтобы начать
          </p>
        </div>
      </div>
    </div>
  );
}

export default WelcomeScreen;

