import { useState, useEffect } from 'react';
import { API_URL } from '../../config';
import '../../css/components/SettingsContent.css';

const SettingsContent = ({ selectedSetting, email, onChatDataUpdate }) => {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });
  const [formData, setFormData] = useState({
    username: '',
    bio: '',
    notification_anon_chats: true,
    notification_open_chats: true,
    old_password: '',
    new_password: '',
    new_password_confirm: '',
  });
  const [blacklist, setBlacklist] = useState([]);
  const [blacklistInput, setBlacklistInput] = useState('');


  useEffect(() => {
    if (email) {
      loadUserData();
      if (selectedSetting?.name === 'Черный список') {
        loadBlacklist();
      }
    }
  }, [email, selectedSetting]);

  const loadUserData = async () => {
    console.log('Loading user data for email:', email);
    try {
      const url = `${API_URL}/settings/${email}`;
      console.log('Fetching:', url);
      const response = await fetch(url);
      console.log('Response status:', response.status);
      
      if (response.ok) {
        const data = await response.json();
        console.log('Loaded user data:', data);
        setFormData(prev => ({
          ...prev,
          username: data.nickname || data.username || localStorage.getItem('nickname') || '',
          bio: data.bio || '',
          notification_anon_chats: data.notification_anon_chats ?? true,
          notification_open_chats: data.notification_open_chats ?? true,
        }));
      } else {
        console.error('Failed to load user data:', response.status, await response.text());
      }
    } catch (error) {
      console.error('Ошибка загрузки данных:', error);
    }
  };

  const loadBlacklist = async () => {
    console.log('Loading blacklist for email:', email);
    try {
      const url = `${API_URL}/settings/blacklist/${email}`;
      console.log('Fetching blacklist:', url);
      const response = await fetch(url);
      console.log('Blacklist response status:', response.status);
      
      if (response.ok) {
        const data = await response.json();
        console.log('Loaded blacklist:', data);
        setBlacklist(data);
      } else {
        console.error('Failed to load blacklist:', response.status, await response.text());
      }
    } catch (error) {
      console.error('Ошибка загрузки черного списка:', error);
    }
  };

  const showMessage = (text, type) => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: '', type: '' }), 5000);
  };

  const renderAlert = () => (
    message.text ? (
      <div className={`settings-alert ${message.type}`}>
        {message.text}
      </div>
    ) : null
  );



  const handleUpdateUsername = async () => {
    if (!formData.username || formData.username.length < 3) {
      showMessage('Никнейм должен быть не менее 3 символов', 'error');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/settings/profile/nickname/${email}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nickname: formData.username }),
      });

      const data = await response.json();
      if (data.success) {
        showMessage('Никнейм изменен', 'success');
        if (data.chat_data && onChatDataUpdate) {
          onChatDataUpdate(data.chat_data);
        }

        localStorage.setItem('nickname', formData.username);
      } else {
        showMessage(data.message || 'Никнейм занят', 'error');
      }
    } catch (error) {
      showMessage('Ошибка обновления никнейма', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateBio = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/settings/profile/bio/${email}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bio: formData.bio || null }),
      });

      const data = await response.json();
      if (data.success) {
        showMessage('Информация изменена', 'success');
      } else {
        showMessage(data.message || 'Недопустимые символы или слишком большой размер текста', 'error');
      }
    } catch (error) {
      showMessage('Ошибка обновления информации', 'error');
    } finally {
      setLoading(false);
    }
  };



  const handleUpdateNotifications = async (field, value) => {
    console.log('Updating notifications:', field, value);
    setLoading(true);
    try {
      const url = `${API_URL}/settings/notifications/${email}`;
      console.log('Updating notifications at:', url);
      const response = await fetch(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          [field]: value,
        }),
      });

      const data = await response.json();
      console.log('Notification update response:', data);
      if (data.success) {
        setFormData(prev => ({ ...prev, [field]: value }));
        console.log('Notifications updated successfully');
      } else {
        console.error('Failed to update notifications:', data.message);
      }
    } catch (error) {
      console.error('Ошибка обновления настроек уведомлений:', error);
    } finally {
      setLoading(false);
    }
  };



  const handleChangePassword = async () => {
    if (!formData.old_password || !formData.new_password || !formData.new_password_confirm) {
      showMessage('Заполните все поля', 'error');
      return;
    }

    if (formData.new_password !== formData.new_password_confirm) {
      showMessage('Новый пароль и подтверждение не совпадают', 'error');
      return;
    }

    if (formData.new_password.length < 8) {
      showMessage('Новый пароль должен быть не менее 8 символов', 'error');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/settings/account/password/${email}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          old_password: formData.old_password,
          new_password: formData.new_password,
          new_password_confirm: formData.new_password_confirm,
        }),
      });

      const data = await response.json();
      if (response.ok && data.success) {
        showMessage('Пароль изменён. Войдите снова для продолжения.', 'success');
        setFormData(prev => ({
          ...prev,
          old_password: '',
          new_password: '',
          new_password_confirm: '',
        }));
      } else {
        showMessage(data.message || 'Не удалось изменить пароль', 'error');
      }
    } catch (error) {
      showMessage('Ошибка изменения пароля', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('email');
    localStorage.removeItem('nickname');
    localStorage.removeItem('chat_data');
    window.location.href = '/signin';
  };



  const handleAddToBlacklist = async () => {
    const nicknameToBlock = blacklistInput.trim();

    if (!nicknameToBlock) {
      showMessage('Введите никнейм пользователя', 'error');
      return;
    }
    const nickname = localStorage.getItem('nickname') || '';
    if (nicknameToBlock === nickname) {
      showMessage('Нельзя заблокировать свой аккаунт', 'error');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/settings/blacklist/${email}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: nicknameToBlock }),
      });

      const data = await response.json();
      if (data.success) {
        showMessage('Пользователь добавлен в черный список', 'success');
        setBlacklistInput('');
        loadBlacklist();
      } else {
        showMessage(data.message || 'Ошибка добавления в черный список', 'error');
      }
    } catch (error) {
      showMessage('Ошибка добавления в черный список', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveFromBlacklist = async (blockedUsername) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/settings/blacklist/${email}?blocked_username=${blockedUsername}`, {
        method: 'DELETE',
      });

      const data = await response.json();
      if (data.success) {
        setBlacklist(prev => prev.filter(u => (u.nickname || u.username) !== blockedUsername));
        showMessage('Пользователь удален из черного списка', 'success');
      } else {
        showMessage(data.message || 'Ошибка удаления', 'error');
      }
    } catch (error) {
      showMessage('Ошибка удаления из черного списка', 'error');
    } finally {
      setLoading(false);
    }
  };



  if (!selectedSetting) {
    return (
      <div className="settings-content settings-content-empty">
        <div className="empty-state">
          <p>Выберите настройку</p>
        </div>
      </div>
    );
  }

  const renderContent = () => {
    switch (selectedSetting.name) {
      case 'Профиль':
        return (
          <div className="settings-section">
            {renderAlert()}
            <h2>Профиль</h2>
            
            {}
            <div className="settings-field">
              <label>Отображаемый никнейм</label>
              <div className="settings-field-row">
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData(prev => ({ ...prev, username: e.target.value }))}
                  placeholder="Введите никнейм"
                />
                <button onClick={handleUpdateUsername} disabled={loading}>
                  Изменить
                </button>
              </div>
            </div>

            {}
            <div className="settings-field">
              <label>Отображаемая информация о себе</label>
              <div className="settings-field-row">
                <textarea
                  value={formData.bio}
                  onChange={(e) => setFormData(prev => ({ ...prev, bio: e.target.value }))}
                  placeholder="Любая информация, например возраст, местоположение и т.д."
                  rows={4}
                />
                <button onClick={handleUpdateBio} disabled={loading}>
                  Изменить
                </button>
              </div>
            </div>
          </div>
        );

      case 'Уведомления':
        return (
          <div className="settings-section">
            {renderAlert()}
            <h2>Уведомления</h2>
            
            <div className="settings-field">
              <div className="toggle-field">
                <label>Уведомления из анонимных чатов</label>
                <div
                  className={`toggle-switch ${formData.notification_anon_chats ? 'on' : 'off'}`}
                  onClick={() => handleUpdateNotifications('notification_anon_chats', !formData.notification_anon_chats)}
                >
                  <div className="toggle-slider"></div>
                </div>
              </div>
            </div>

            <div className="settings-field">
              <div className="toggle-field">
                <label>Уведомления из открытых чатов</label>
                <div
                  className={`toggle-switch ${formData.notification_open_chats ? 'on' : 'off'}`}
                  onClick={() => handleUpdateNotifications('notification_open_chats', !formData.notification_open_chats)}
                >
                  <div className="toggle-slider"></div>
                </div>
              </div>
            </div>
          </div>
        );

      case 'Аккаунт':
        return (
          <div className="settings-section">
            {renderAlert()}
            <h2>Аккаунт</h2>
            
            <div className="settings-field">
              <h3>Смена пароля</h3>
              <div className="password-fields">
                <input
                  type="password"
                  placeholder="Старый пароль"
                  value={formData.old_password}
                  onChange={(e) => setFormData(prev => ({ ...prev, old_password: e.target.value }))}
                />
                <input
                  type="password"
                  placeholder="Новый пароль"
                  value={formData.new_password}
                  onChange={(e) => setFormData(prev => ({ ...prev, new_password: e.target.value }))}
                />
                <input
                  type="password"
                  placeholder="Новый пароль еще раз"
                  value={formData.new_password_confirm}
                  onChange={(e) => setFormData(prev => ({ ...prev, new_password_confirm: e.target.value }))}
                />
                <button onClick={handleChangePassword} disabled={loading} className="primary-button">
                  Изменить пароль
                </button>
              </div>
            </div>

            <div className="settings-field">
              <button onClick={handleLogout} className="danger-button">
                Выйти из аккаунта
              </button>
            </div>
          </div>
        );

      case 'Черный список':
        return (
          <div className="settings-section">
            {renderAlert()}
            <h2>Черный список</h2>
            
            <div className="settings-field">
              <label>Добавить пользователя в черный список</label>
              <div className="blacklist-input-group">
                <input
                  type="text"
                  value={blacklistInput}
                  onChange={(e) => setBlacklistInput(e.target.value)}
                  placeholder="@никнейм"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddToBlacklist();
                    }
                  }}
                />
                <button onClick={handleAddToBlacklist} disabled={loading}>
                  Добавить
                </button>
              </div>
              <p className="field-hint">Пользователь не сможет отправлять вам сообщения и видеть вас в поиске.</p>
            </div>
            
            {blacklist.length === 0 ? null : (
              <div className="blacklist-items">
                {blacklist.map((user) => {
                  const userNickname = user.nickname || user.username || '';
                  return (
                  <div key={user.id} className="blacklist-item">
                      <div className="blacklist-user-info" title={userNickname}>
                      <div className="blacklist-avatar placeholder">
                          <span>{userNickname?.charAt(0)?.toUpperCase()}</span>
                      </div>
                      <div className="blacklist-text">
                        <span className="blacklist-username">
                            {userNickname.length > 24 ? `${userNickname.slice(0, 24)}…` : userNickname}
                        </span>
                        <span className="blacklist-status">Заблокирован</span>
                      </div>
                    </div>
                    <button
                        onClick={() => handleRemoveFromBlacklist(userNickname)}
                      disabled={loading}
                      className="remove-button"
                    >
                      Разблокировать
                    </button>
                  </div>
                  );
                })}
              </div>
            )}
          </div>
        );

      default:
        return (
          <div className="settings-section">
            <p>Настройка "{selectedSetting.name}" в разработке</p>
          </div>
        );
    }
  };

  return (
    <div className="settings-content">
      {renderContent()}
    </div>
  );
};

export default SettingsContent;

