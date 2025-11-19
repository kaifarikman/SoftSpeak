import { useState } from 'react';
import ChatItem from './ChatItem';

function ChatList({ chats, selectedChat, setSelectedChat }) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredChats = chats.filter(chat =>
    chat.name.toLowerCase().includes(searchQuery.toLowerCase())
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
        {filteredChats.length > 0 ? (
          filteredChats.map(chat => (
            <ChatItem
              key={chat.id}
              chat={chat}
              isSelected={selectedChat?.id === chat.id}
              onClick={() => setSelectedChat(chat)}
            />
          ))
        ) : (
          <div className="empty-state">
            <p>Нет чатов</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default ChatList;