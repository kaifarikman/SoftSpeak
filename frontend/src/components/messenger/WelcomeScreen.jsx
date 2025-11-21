import '../../css/components/WelcomeScreen.css';

function WelcomeScreen({ username, onSelectSection }) {
  const features = [
    { id: 'bot', emoji: '🤖', title: 'AI Чат-бот', description: 'Умный ассистент для психологической поддержки' },
    { id: 'anon', emoji: '🎭', title: 'Анонимные чаты', description: 'Найдите собеседника и общайтесь инкогнито' },
    { id: 'people', emoji: '👥', title: 'Публичные чаты', description: 'Раскройте личность и продолжите общение' },
    { id: 'settings', emoji: '⚙️', title: 'Настройки', description: 'Персонализируйте профиль и предпочтения' },
  ];

  const handleFeatureClick = (sectionId) => {
    if (typeof onSelectSection === 'function') {
      onSelectSection(sectionId);
    }
  };

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
            <p className="greeting-text">
              Добро пожаловать, <span className="username-highlight">{username}</span>!
            </p>
          </div>
        )}

        <div className="welcome-features">
          {features.map((feature) => (
            <button
              key={feature.id}
              type="button"
              className="feature-item"
              onClick={() => handleFeatureClick(feature.id)}
            >
              <div className="feature-emoji">{feature.emoji}</div>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
            </button>
          ))}
        </div>

        <div className="welcome-instruction">
          <p className="instruction-text">
            Нажмите на любой из разделов, чтобы перейти к нужной функции
          </p>
        </div>
      </div>
    </div>
  );
}

export default WelcomeScreen;

