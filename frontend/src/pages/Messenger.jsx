import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Navigation from '../components/messenger/Navigation';
import ChatArea from '../components/messenger/ChatArea';
import WelcomeScreen from '../components/messenger/WelcomeScreen';
import ChatList from '../components/messenger/ChatList';
import ChatListAnon from '../components/messenger/ChatListAnon';
import SettingsList from '../components/messenger/SettingsList';
import BannedOverlay from '../components/BannedOverlay';
import { useChatData } from '../context/ChatDataContext';
import { API_URL } from '../config';
import { logError, handleApiError } from '../utils/errorHandler';
import '../css/Messenger.css';
import '../css/components/ChatArea.css';
import '../css/components/ChatHeader.css';
import '../css/components/ChatItem.css';
import '../css/components/ChatList.css';
import '../css/components/ChatListAnon.css';
import '../css/components/Message.css';
import '../css/components/MessageInput.css';
import '../css/components/MessageList.css';
import '../css/components/Navigation.css';
import '../css/components/SettingsContent.css';
import '../css/components/WelcomeScreen.css';

function Messenger() {
  const navigate = useNavigate();

  const { chatData, updateChatData } = useChatData();
  const [activeSection, setActiveSection] = useState('bot');
  const [selectedChatBot, setSelectedChatBot] = useState("SoftSpeak");
  const [selectedChatAnon, setSelectedChatAnon] = useState(null);
  const [selectedChatPeople, setSelectedChatPeople] = useState(null);
  const [selectedChatSettings, setSelectedChatSettings] = useState(null);
  const [isBanned, setIsBanned] = useState(false);
  const [isCheckingBan, setIsCheckingBan] = useState(true);

  useEffect(() => {
    const savedChatData = localStorage.getItem('chat_data');
    if (savedChatData) {
      try {
        const parsed = JSON.parse(savedChatData);
        updateChatData(parsed);
      } catch (err) {
        console.error('Ошибка парсинга chat_data:', err);
      }
    }

  }, []);

  // Функция проверки статуса пользователя
  const checkUserStatus = useCallback(async () => {
    const username = localStorage.getItem('username');
    if (!username) return;

    try {
      const response = await fetch(`${API_URL}/settings/status/${username}`);
      if (response.ok) {
        const data = await response.json();
        if (!data.is_active) {
          setIsBanned(true);
          window.dispatchEvent(new Event('userBanned'));
          return true; // Пользователь забанен
        } else {
          setIsBanned(false);
          return false;
        }
      } else if (response.status === 403) {
        // Пользователь забанен
        setIsBanned(true);
        window.dispatchEvent(new Event('userBanned'));
        return true;
      } else {
        // Другая ошибка, но не бан
        setIsBanned(false);
        return false;
      }
    } catch (error) {
      console.error('Ошибка проверки статуса пользователя:', error);
      // При ошибке не блокируем доступ, но логируем
      setIsBanned(false);
      return false;
    }
  }, []);

  // Обработчик события бана из других компонентов
  useEffect(() => {
    const handleBanned = () => {
      setIsBanned(true);
    };
    
    window.addEventListener('userBanned', handleBanned);
    return () => window.removeEventListener('userBanned', handleBanned);
  }, []);

  useEffect(() => {
    const username = localStorage.getItem('username');
    if (!username) {
      navigate('/signin');
      return;
    }

    // Проверяем статус пользователя при загрузке страницы
    checkUserStatus().finally(() => {
      setIsCheckingBan(false);
    });
    
    // Проверяем статус периодически (каждые 10 секунд для более быстрого обнаружения бана)
    const interval = setInterval(() => {
      checkUserStatus();
    }, 10000);
    
    // Проверяем статус при возврате фокуса на окно
    const handleFocus = () => {
      checkUserStatus();
    };
    
    // Проверяем статус при видимости страницы
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        checkUserStatus();
      }
    };
    
    window.addEventListener('focus', handleFocus);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      clearInterval(interval);
      window.removeEventListener('focus', handleFocus);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [navigate, checkUserStatus]);


  const chatBot = {
    id: 1,
    name: "SoftSpeak",
  };
  const settingsChats = [
    { id: 1, name: "Профиль" },
    { id: 2, name: "Уведомления" },
    { id: 3, name: "Аккаунт" },
    { id: 4, name: "Черный список" }
  ];
  
  const [chatsPeople, setChatsPeople] = useState([]);
  const [chatsAnon, setChatsAnon] = useState([]);
  const username = localStorage.getItem('username') || '';


  useEffect(() => {
    setChatsPeople([]);
    setChatsAnon([]);
    setSelectedChatAnon(null);
    setSelectedChatPeople(null);
  }, [username]);

  const fetchPublicChats = useCallback(async () => {
    if (!username) return;

    try {
      const response = await fetch(`${API_URL}/matchmaking/public-chats/${username}`);
      if (response.status === 403) {
        // Пользователь забанен
        setIsBanned(true);
        window.dispatchEvent(new Event('userBanned'));
        return;
      }
      if (response.ok) {
        const data = await response.json();
        const formatted = data.map(chat => ({
          id: chat.id,
          name: chat.name,
          avatar: chat.avatar || '',
          lastMessage: chat.last_message || '',
          lastMessageTime: chat.last_message_time
            ? new Date(chat.last_message_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
            : '',
          unreadCount: chat.unread_count || 0,
        }));
        setChatsPeople(formatted);
      }
    } catch (error) {
      logError(error, 'Messenger fetchPublicChats');
    }
  }, [username]);

  useEffect(() => {
    if (!username) return;

    fetchPublicChats();
    const interval = setInterval(fetchPublicChats, 300000);
    return () => clearInterval(interval);
  }, [username, fetchPublicChats]);










  const handleNotificationClick = useCallback(async (notification) => {
    if (!username) return;

    try {
      const response = await fetch(`${API_URL}/matchmaking/chat/${notification.chat_id}/read/${username}`, {
        method: 'PUT',
      });
      
      if (response.status === 403) {
        // Пользователь забанен
        setIsBanned(true);
        return;
      }
      
      if (response.ok) {
        if (notification.chat_type === 'anon') {
          const chatsResponse = await fetch(`${API_URL}/matchmaking/chats/${username}`);
          if (chatsResponse.ok) {
            const chatsData = await chatsResponse.json();
            const chat = chatsData.find(c => c.id === notification.chat_id);
            if (chat) {
              setChatsAnon(prev => {
                const filtered = prev.filter(c => c.id !== notification.chat_id);
                return [chat, ...filtered];
              });
              setSelectedChatAnon(chat);
              setActiveSection('anon');
            }
          }
        } else if (notification.chat_type === 'people') {
          const chatsResponse = await fetch(`${API_URL}/matchmaking/public-chats/${username}`);
          if (chatsResponse.ok) {
            const chatsData = await chatsResponse.json();
            const chat = chatsData.find(c => c.id === notification.chat_id);
            if (chat) {
              const formattedChat = {
                id: chat.id,
                name: chat.name,
                avatar: chat.avatar || '',
                lastMessage: chat.last_message || '',
                lastMessageTime: chat.last_message_time
                  ? new Date(chat.last_message_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
                  : '',
                unreadCount: 0,
              };
              setChatsPeople(prev => {
                const filtered = prev.filter(c => c.id !== notification.chat_id);
                return [formattedChat, ...filtered];
              });
              setSelectedChatPeople(formattedChat);
              setActiveSection('people');
            }
          }
        }
      }
    } catch (err) {
      logError(err, 'Messenger handleNotificationClick');
    }
  }, [username]);

  const handleSectionChange = (newSection) => {

    if (chatData) {
      // Блокируем переход к боту если AI отключен или опрос завершен (есть история и messengers доступны)
      if (newSection === 'bot' && (
        chatData.ai === false || 
        (Array.isArray(chatData.ai) && chatData.ai.length > 0 && chatData.messengers === true)
      )) {
        return;
      }
      if ((newSection === 'people' || newSection === 'anon') && !chatData.messengers) {

        return;
      }
      if (newSection === 'settings' && !chatData.settings) {

        return;
      }
    }
    
    setActiveSection(newSection);
    

    if (newSection === 'bot') {
      setSelectedChatBot("SoftSpeak");
    } else if (newSection === 'anon') {
      setSelectedChatAnon(null);
    } else if (newSection === 'people') {
      setSelectedChatPeople(null);
    } else if (newSection === 'settings') {
      setSelectedChatSettings(null);
    }
  };

const getActiveChatData = () => {
    switch (activeSection) {
      case 'bot':
        return {
          selectedChat: chatBot,
          setSelectedChat: setSelectedChatBot,
          chats: [chatBot],
        };
      case 'anon':
        return {
          selectedChat: selectedChatAnon,
          setSelectedChat: setSelectedChatAnon,
          chats: chatsAnon.length > 0 ? chatsAnon : [],
        };
      case 'people':
        return {
          selectedChat: selectedChatPeople,
          setSelectedChat: setSelectedChatPeople,
          chats: chatsPeople,
        };
      case 'settings':
        return {
          chats: settingsChats,
          selectedChat: selectedChatSettings,
          setSelectedChat: setSelectedChatSettings
        };
      default:
        return {
          selectedChat: null,
          setSelectedChat: () => {},
          chats: [],
        };
    }
  };

  const activeChatData = getActiveChatData();
  const isAnonChatFocused = activeSection === 'anon' && selectedChatAnon;
  

  const showWelcomeScreen = !activeSection;

  const renderListPanel = () => {
    if (!activeSection) return null;

    if (activeSection === 'people') {
      return (
        <ChatList
          chats={activeChatData.chats}
          selectedChat={activeChatData.selectedChat}
          setSelectedChat={activeChatData.setSelectedChat}
        />
      );
    }

    if (activeSection === 'anon') {
      return (
        <ChatListAnon
          chats={activeChatData.chats}
          selectedChat={activeChatData.selectedChat}
          setSelectedChat={activeChatData.setSelectedChat}
          username={username}
          onChatsUpdate={setChatsAnon}
        />
      );
    }

    if (activeSection === 'settings') {
      return (
        <SettingsList
          settings={activeChatData.chats}
          selectedChat={activeChatData.selectedChat}
          setSelectedChat={activeChatData.setSelectedChat}
        />
      );
    }

    return null;
  };

  const shouldHideList =
    showWelcomeScreen ||
    activeSection === 'bot' ||
    (activeSection === 'anon' && Boolean(selectedChatAnon));

  // Показываем overlay если пользователь забанен
  if (isBanned) {
    return <BannedOverlay />;
  }

  // Показываем загрузку пока проверяем статус
  if (isCheckingBan) {
    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '100vh',
        background: '#0f1117',
        color: '#cbd5e1'
      }}>
        Загрузка...
      </div>
    );
  }

  return (
    <div className="messenger-container">
      <Navigation
        activeSection={activeSection}
        setActiveSection={handleSectionChange}
        chatData={chatData}
        username={username}
        onNotificationClick={handleNotificationClick}
      />
      <div className="messenger-body">
        {!shouldHideList && (
          <div className="messenger-list">
            {renderListPanel()}
          </div>
        )}
        {activeSection === 'bot' ? (
          // Для бота ChatArea рендерится напрямую в messenger-body без обертки messenger-chat
          showWelcomeScreen ? (
            <WelcomeScreen username={username} onSelectSection={handleSectionChange} />
          ) : (
            <ChatArea
              selectedChat={activeChatData.selectedChat}
              activeSection={activeSection}
              chatData={chatData}
              username={username}
              onChatDataUpdate={updateChatData}
              isStandalone={true}
              onAnonChatExit={() => {}}
              onChatRevealed={() => {}}
            />
          )
        ) : (
          <div className={`messenger-chat ${shouldHideList ? 'messenger-chat-fullwidth' : ''}`}>
          {showWelcomeScreen ? (
            <WelcomeScreen username={username} onSelectSection={handleSectionChange} />
          ) : (
            <ChatArea
              selectedChat={activeChatData.selectedChat}
              activeSection={activeSection}
              chatData={chatData}
              username={username}
              onChatDataUpdate={updateChatData}
              isStandalone={activeSection === 'anon' && Boolean(selectedChatAnon)}
              onAnonChatExit={() => {
                setSelectedChatAnon(null);
              }}
              onChatRevealed={(publicChat) => {
                setChatsAnon(prev => prev.filter(chat => chat.id !== publicChat.id));
                setChatsPeople(prev => {
                  const filtered = prev.filter(chat => chat.id !== publicChat.id);
                  return [publicChat, ...filtered];
                });
                setSelectedChatAnon(null);
                setSelectedChatPeople(publicChat);
                setActiveSection('people');
              }}
            />
          )}
        </div>
        )}
      </div>
    </div>
  );
}

export default Messenger;

