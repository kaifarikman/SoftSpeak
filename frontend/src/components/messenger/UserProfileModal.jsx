import { useState, useEffect } from 'react';
import { API_URL } from '../../config';
import '../../css/components/UserProfileModal.css';

function UserProfileModal({ nickname, isOpen, onClose }) {
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && nickname) {
      loadUserProfile();
    } else {
      setProfileData(null);
      setError(null);
    }
  }, [isOpen, nickname]);

  const loadUserProfile = async () => {
    if (!nickname) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Используем email для получения данных пользователя по nickname
      const email = localStorage.getItem('email') || '';
      if (!email) return;
      // Ищем пользователя по nickname через API настроек
      // Временное решение: используем email текущего пользователя, если nickname совпадает
      const response = await fetch(`${API_URL}/settings/${email}`);
      if (response.ok) {
        const data = await response.json();
        setProfileData(data);
      } else {
        setError('Не удалось загрузить профиль');
      }
    } catch (err) {
      setError('Ошибка загрузки профиля');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const userInitial = (nickname || 'U').charAt(0).toUpperCase();

  return (
    <>
      <div className="user-profile-modal-overlay" onClick={onClose} />
      <div className="user-profile-modal">
        <div className="user-profile-modal-header">
          <button className="user-profile-modal-back" onClick={onClose}>
            ← Назад
          </button>
        </div>
        
        <div className="user-profile-modal-content">
          {loading ? (
            <div className="user-profile-modal-loading">
              <p>Загрузка...</p>
            </div>
          ) : error ? (
            <div className="user-profile-modal-error">
              <p>{error}</p>
            </div>
          ) : profileData ? (
            <>
              <div className="user-profile-avatar">
                <div className="user-profile-avatar-placeholder">
                  <span>{userInitial}</span>
                </div>
              </div>
              
              <div className="user-profile-info">
                <h2 className="user-profile-username">{profileData.nickname || profileData.username}</h2>
                
                {profileData.bio ? (
                  <div className="user-profile-bio">
                    <p>{profileData.bio}</p>
                  </div>
                ) : (
                  <div className="user-profile-bio-empty">
                    <p>Информация о пользователе отсутствует</p>
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </>
  );
}

export default UserProfileModal;

