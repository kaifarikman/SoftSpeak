import { useState, useEffect, useCallback } from 'react';
import { API_URL } from '../../config';
import '../../css/components/UserProfileModal.css';

function UserProfileModal({ nickname, isOpen, onClose }) {
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadUserProfile = useCallback(async () => {
    if (!nickname) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Получаем публичный профиль пользователя по nickname
      const response = await fetch(`${API_URL}/settings/profile/by-nickname/${encodeURIComponent(nickname)}`);
      if (response.ok) {
        const data = await response.json();
        setProfileData(data);
      } else {
        // Если не удалось загрузить, показываем хотя бы nickname
        setProfileData({
          nickname: nickname,
          bio: null
        });
      }
    } catch (err) {
      console.error('Ошибка загрузки профиля:', err);
      // Показываем хотя бы nickname при ошибке
      setProfileData({
        nickname: nickname,
        bio: null
      });
    } finally {
      setLoading(false);
    }
  }, [nickname]);

  useEffect(() => {
    if (isOpen && nickname) {
      loadUserProfile();
    } else {
      setProfileData(null);
      setError(null);
    }
  }, [isOpen, nickname, loadUserProfile]);

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

