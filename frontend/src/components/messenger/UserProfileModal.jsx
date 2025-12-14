import { useState, useEffect, useCallback } from 'react';
import { API_URL } from '../../config';
import '../../css/components/UserProfileModal.css';

function UserProfileModal({ nickname, isOpen, onClose }) {
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadUserProfile = useCallback(async () => {
    if (!nickname) {
      console.warn('UserProfileModal: nickname не предоставлен');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {

      const url = `${API_URL}/settings/profile/by-nickname/${encodeURIComponent(nickname)}`;
      console.log('UserProfileModal: Загрузка профиля для', nickname, 'URL:', url);
      
      const response = await fetch(url);
      console.log('UserProfileModal: Ответ сервера', response.status, response.statusText);
      
      if (response.ok) {
        const data = await response.json();
        console.log('UserProfileModal: Данные профиля получены', data);
        setProfileData(data);
      } else {
        const errorText = await response.text();
        console.error('UserProfileModal: Ошибка загрузки профиля', response.status, errorText);
        setError(`Не удалось загрузить профиль: ${response.status}`);

        setProfileData({
          nickname: nickname,
          bio: null
        });
      }
    } catch (err) {
      console.error('UserProfileModal: Ошибка загрузки профиля:', err);
      setError('Ошибка при загрузке профиля');

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

