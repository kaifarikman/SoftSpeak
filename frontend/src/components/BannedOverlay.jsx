import '../css/components/BannedOverlay.css';

function BannedOverlay() {
  const handleLogout = () => {
    localStorage.clear();
    window.location.href = '/signin';
  };

  return (
    <div className="banned-overlay">
      <div className="banned-overlay-content">
        <div className="banned-icon">🚫</div>
        <h1 className="banned-title">Вы забанены</h1>
        <p className="banned-message">
          Ваш аккаунт заблокирован администратором. Доступ к сайту запрещен.
        </p>
        <button className="banned-logout-button" onClick={handleLogout}>
          Выйти из аккаунта
        </button>
      </div>
    </div>
  );
}

export default BannedOverlay;

