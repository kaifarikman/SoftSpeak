import botIcon from '../../assets/icons/chatbot.png';
import anonIcon from '../../assets/icons/masks.png';
import peopleIcon from '../../assets/icons/people.png';
import settingsIcon from '../../assets/icons/settings.png';
import { API_URL } from '../../config';

function Navigation({ activeSection, setActiveSection, chatData, isOpen, onClose }) {
  const sections = [
     { id: 'bot', icon: botIcon, title: 'Бот' },
    { id: 'anon', icon: anonIcon, title: 'Анонимные' },
    { id: 'people', icon: peopleIcon, title: 'Люди' },
    { id: 'settings', icon: settingsIcon, title: 'Настройки' }
  ];

  // Фильтруем секции на основе chatData
  const availableSections = sections.filter(section => {
    if (!chatData) return true; // Если данных нет, показываем все
    
    switch (section.id) {
      case 'bot':
        // AI доступен, если ai !== false
        return chatData.ai !== false;
      case 'people':
        // Публичные мессенджеры доступны, если messengers === true
        return chatData.messengers === true;
      case 'anon':
        // Анонимные мессенджеры доступны, если messengers === true
        return chatData.messengers === true;
      case 'settings':
        // Settings доступен, если settings === true
        return chatData.settings === true;
      default:
        return true;
    }
  });

  // Формируем URL для аватара
  const getAvatarUrl = () => {
    if (!chatData?.avatar) {
      console.log('Navigation: No avatar in chatData');
      return null;
    }
    const avatar = chatData.avatar;
    console.log('Navigation: Avatar from chatData:', avatar);
    
    if (avatar.startsWith('http')) {
      console.log('Navigation: Using full HTTP URL');
      return avatar;
    }
    if (avatar.startsWith('/static') || avatar.startsWith('/')) {
      // Статические файлы уже проксируются через Nginx, используем как есть
      console.log('Navigation: Using path as-is (proxied by Nginx):', avatar);
      return avatar;
    }
    // Если нет слеша в начале, добавляем
    const fullUrl = `/${avatar}`;
    console.log('Navigation: Added leading slash:', fullUrl);
    return fullUrl;
  };

  const avatarUrl = getAvatarUrl();
  console.log('Navigation: Final avatar URL:', avatarUrl);

  return (
    <>
      {/* Оверлей для закрытия меню на мобильных */}
      <div 
        className={`navigation-overlay ${isOpen ? 'visible' : ''}`}
        onClick={onClose}
      ></div>
      
      <div className={`navigation ${isOpen ? 'open' : ''}`}>
      <div className="user-avatar">
        {avatarUrl ? (
          <div className="avatar-circle" style={{ position: 'relative', overflow: 'hidden' }}>
            <img 
              src={avatarUrl}
              alt="User avatar"
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                position: 'absolute',
                top: 0,
                left: 0
              }}
              onError={(e) => {
                console.error('Ошибка загрузки аватара в Navigation:', avatarUrl);
                e.target.style.display = 'none';
              }}
            />
          </div>
        ) : (
          <div className="avatar-circle"></div>
        )}
      </div>
      <div className="nav-items">
        {availableSections.map(section => (
          <button
          key={section.id}
          className={`nav-item ${activeSection === section.id ? 'active' : ''}`}
          onClick={() => setActiveSection(section.id)}
          title={section.title}
        >
           <div
              className={`nav-icon-img ${section.id}`}
            ></div>
          </button>
        ))}
      </div>
    </div>
    </>
  );
}

export default Navigation;