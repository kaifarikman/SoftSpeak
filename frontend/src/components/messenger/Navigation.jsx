import { useEffect, useMemo, useState } from 'react';
import botIcon from '../../assets/icons/chatbot.png';
import anonIcon from '../../assets/icons/masks.png';
import peopleIcon from '../../assets/icons/people.png';
import settingsIcon from '../../assets/icons/settings.png';
import { resolveStaticUrl } from '../../utils/url';
import { API_URL } from '../../config';

const NAV_SECTIONS = [
  { id: 'bot', icon: botIcon, title: 'Бот' },
  { id: 'anon', icon: anonIcon, title: 'Анонимные' },
  { id: 'people', icon: peopleIcon, title: 'Люди' },
  { id: 'settings', icon: settingsIcon, title: 'Настройки' }
];

function Navigation({ activeSection, setActiveSection, chatData, username }) {
  const availableSections = useMemo(() => {
    return NAV_SECTIONS.filter(section => {
      if (!chatData) return true;
      
      switch (section.id) {
        case 'bot':
          return chatData.ai !== false;
        case 'people':
        case 'anon':
          return chatData.messengers === true;
        case 'settings':
          return chatData.settings === true;
        default:
          return true;
      }
    });
  }, [chatData]);

  const [avatarUrl, setAvatarUrl] = useState(() => resolveStaticUrl(chatData?.avatar || ''));
  const [avatarError, setAvatarError] = useState(false);

  useEffect(() => {
    setAvatarError(false);
    setAvatarUrl(resolveStaticUrl(chatData?.avatar || ''));
  }, [chatData?.avatar]);

  useEffect(() => {
    if (avatarUrl || !username) {
      return;
    }

    const controller = new AbortController();

    const fetchAvatar = async () => {
      try {
        const response = await fetch(`${API_URL}/settings/${username}`, {
          signal: controller.signal,
        });
        if (!response.ok) return;
        const data = await response.json();
        if (data?.avatar) {
          setAvatarUrl(resolveStaticUrl(data.avatar));
          setAvatarError(false);
        }
      } catch (error) {
        if (error.name !== 'AbortError') {
          console.warn('Не удалось загрузить аватар пользователя:', error);
        }
      }
    };

    fetchAvatar();

    return () => controller.abort();
  }, [avatarUrl, username]);

  const showInitials = !avatarUrl || avatarError;
  const userInitial = (username || 'U').charAt(0).toUpperCase();

  return (
    <div className="navigation">
      <div className="nav-items">
        {availableSections.map(section => (
          <button
            key={section.id}
            className={`nav-item ${activeSection === section.id ? 'active' : ''}`}
            onClick={() => setActiveSection(section.id)}
            title={section.title}
          >
            <div className={`nav-icon-img ${section.id}`} />
            <span>{section.title}</span>
          </button>
        ))}
      </div>
      <div className="user-avatar" title={username || 'Профиль'}>
        <div className="avatar-circle">
          {showInitials ? (
            <span className="avatar-placeholder">{userInitial}</span>
          ) : (
            <img
              src={avatarUrl}
              alt="User avatar"
              onError={() => setAvatarError(true)}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default Navigation;