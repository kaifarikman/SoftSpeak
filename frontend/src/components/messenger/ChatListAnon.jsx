import { useState, useEffect, memo } from 'react';
import ChatItem from './ChatItem';
import MatchmakingButton from './MatchmakingButton';
import { API_URL } from '../../config';
import { logError, handleApiError } from '../../utils/errorHandler';
import '../../css/components/ChatListAnon.css';
import '../../css/components/MatchmakingButton.css';

const ChatListAnon = memo(({ chats, selectedChat, setSelectedChat, email, onChatsUpdate }) => {
  const [localChats, setLocalChats] = useState(chats || []);

  useEffect(() => {
    if (email) {
      loadChats();

      const interval = setInterval(loadChats, 300000);
      return () => clearInterval(interval);
    }
  }, [email]);

  useEffect(() => {
    if (Array.isArray(chats)) {
      setLocalChats(chats);
    }
  }, [chats]);

  const loadChats = async () => {
    if (!email) return;
    
    try {
      const response = await fetch(`${API_URL}/matchmaking/chats/${email}`);
      if (response.ok) {
        const data = await response.json();

        const formattedChats = data.map(chat => ({
          id: chat.id,
          name: chat.name || 'Собеседник',
          lastMessage: chat.last_message || '',
          lastMessageTime: chat.last_message_time ? new Date(chat.last_message_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : '',
          unreadCount: chat.unread_count || 0,
        }));
        setLocalChats(formattedChats);
        if (onChatsUpdate) {
          onChatsUpdate(formattedChats);
        }
      }
        } catch (error) {
          logError(error, 'ChatListAnon loadChats');
        }
  };

  const handleMatchFound = async (chatId) => {
    console.log('Match found! Chat ID:', chatId);
    
    // Очищаем выбранный чат перед загрузкой нового
    setSelectedChat(null);

    try {
      const response = await fetch(`${API_URL}/matchmaking/chats/${email}`);
      if (response.ok) {
        const data = await response.json();
        const formattedChats = data.map(chat => ({
          id: chat.id,
          name: chat.name || 'Собеседник',
          lastMessage: chat.last_message || '',
          lastMessageTime: chat.last_message_time ? new Date(chat.last_message_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : '',
          unreadCount: chat.unread_count || 0,
        }));
        
        console.log('Loaded chats after match:', formattedChats);
        setLocalChats(formattedChats);
        
        if (onChatsUpdate) {
          onChatsUpdate(formattedChats);
        }
        

        const foundChat = formattedChats.find(chat => chat.id === chatId);
        if (foundChat) {
          console.log('Selecting chat:', foundChat);
          setSelectedChat(foundChat);
        } else {

          console.log('Chat not found immediately, retrying in 500ms...');
          setTimeout(async () => {
            const retryResponse = await fetch(`${API_URL}/matchmaking/chats/${email}`);
            if (retryResponse.ok) {
              const retryData = await retryResponse.json();
            const retryFormattedChats = retryData.map(chat => ({
              id: chat.id,
              name: chat.name || 'Собеседник',
              lastMessage: chat.last_message || '',
              lastMessageTime: chat.last_message_time ? new Date(chat.last_message_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : '',
              unreadCount: chat.unread_count || 0,
            }));
              
              setLocalChats(retryFormattedChats);
              if (onChatsUpdate) {
                onChatsUpdate(retryFormattedChats);
              }
              
              const retryFoundChat = retryFormattedChats.find(chat => chat.id === chatId);
              if (retryFoundChat) {
                console.log('Chat found on retry:', retryFoundChat);
                setSelectedChat(retryFoundChat);
              }
            }
          }, 500);
        }
      }
    } catch (error) {
      logError(error, 'ChatListAnon handleMatchFound');
    }
  };

  return (
    <div className="chat-list-anon">
      <MatchmakingButton 
        email={email} 
        onMatchFound={handleMatchFound}
      />
      {localChats.length === 0 ? (
        <div className="empty-state empty-state-card">
          <p>Выберите чат, чтобы начать общение</p>
        </div>
      ) : (
        <div className="chat-items">
          {localChats.map((chat) => (
            <ChatItem
              key={chat.id}
              chat={chat}
              isSelected={selectedChat && selectedChat.id === chat.id}
              onClick={() => setSelectedChat(chat)}
            />
          ))}
        </div>
      )}
    </div>
  );
});

ChatListAnon.displayName = 'ChatListAnon';

export default ChatListAnon;
