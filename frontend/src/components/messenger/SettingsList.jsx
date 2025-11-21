import { useState } from 'react';
import SettingsItem from './SettingsItem';

function SettingsList({settings, selectedChat, setSelectedChat }) {
  const [searchQuery, setSearchQuery] = useState('');
 
  // Проверяем, что settings является массивом
  const settingsArray = Array.isArray(settings) ? settings : [];
  
  const filteredSettings = settingsArray.filter(setting =>
    setting && setting.name && setting.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="chat-list">
      <div className="chat-list-header">
        <input
          type="text"
          placeholder="Поиск"
          className="search-input"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>
      <div className="chats">
        {filteredSettings.length > 0 ? (
          filteredSettings.map(setting => (
            <SettingsItem
              key={setting.id}
              chat={setting}
              isSelected={selectedChat?.id === setting.id}
              onClick={() => setSelectedChat(setting)}
            />
          ))
        ) : (
          <div className="empty-state empty-state-card">
            <p>Выберите чат, чтобы начать общение</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default SettingsList;