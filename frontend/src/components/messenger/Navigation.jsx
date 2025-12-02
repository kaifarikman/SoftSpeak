import { useMemo } from 'react';
import botIcon from '../../assets/icons/chatbot.png';
import anonIcon from '../../assets/icons/masks.png';
import peopleIcon from '../../assets/icons/people.png';
import settingsIcon from '../../assets/icons/settings.png';

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
          </button>
        ))}
      </div>
      <div className="user-avatar" title={username || 'Профиль'}>
        <div className="avatar-circle">
          <span className="avatar-placeholder">{userInitial}</span>
        </div>
      </div>
    </div>
  );
}

export default Navigation;