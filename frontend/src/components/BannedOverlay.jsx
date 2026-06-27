import '../css/components/BannedOverlay.css';
import { API_URL } from '../config';
import { apiFetch, clearAuthStorage } from '../utils/apiHelper';

function BannedOverlay() {
  const handleLogout = async () => {
    try {
      await apiFetch(`${API_URL}/auth/logout`, { method: 'POST' });
    } catch (error) {
      console.error('Ошибка выхода:', error);
    }
    clearAuthStorage();
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
