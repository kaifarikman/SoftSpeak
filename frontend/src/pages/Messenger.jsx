import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Navigation from '../components/messenger/Navigation';
import ChatArea from '../components/messenger/ChatArea';
import WelcomeScreen from '../components/messenger/WelcomeScreen';
import ChatList from '../components/messenger/ChatList';
import ChatListAnon from '../components/messenger/ChatListAnon';
import SettingsList from '../components/messenger/SettingsList';
import { useChatData } from '../context/ChatDataContext';
import { API_URL } from '../config';
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
  // Используем Context API вместо прямого доступа к localStorage
  const { chatData, updateChatData } = useChatData();
  const [activeSection, setActiveSection] = useState(null); // bot, anon, people, settings, null = welcome
  const [selectedChatBot, setSelectedChatBot] = useState("SoftSpeak");
  const [selectedChatAnon, setSelectedChatAnon] = useState(null);
  const [selectedChatPeople, setSelectedChatPeople] = useState(null);
  const [selectedChatSettings, setSelectedChatSettings] = useState(null);

  // Принудительно синхронизируем chatData при монтировании
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Выполняется только при монтировании

  useEffect(() => {
    // Проверяем авторизацию
    const username = localStorage.getItem('username');
    if (!username) {
      // Если пользователь не авторизован, перенаправляем на страницу входа
      navigate('/signin');
      return;
    }
    
    // Не устанавливаем начальную секцию - показываем WelcomeScreen
    // Пользователь сам выберет нужный раздел
  }, [chatData, navigate]);

  // Данные для чатов
  const chatBot = {
    id: 1,
    name: "SoftSpeak",
  };
  const settingsChats = [
    { id: 1, name: "Профиль" },
    { id: 2, name: "Уведомления" },
    { id: 3, name: "Медиа" },
    { id: 4, name: "Аккаунт" },
    { id: 5, name: "Черный список" }
  ];
  
  const [chatsPeople, setChatsPeople] = useState([]); // Загружается из API
  const [chatsAnon, setChatsAnon] = useState([]); // Загружается из API
  const username = localStorage.getItem('username') || '';

  // Очищаем состояния чатов при смене пользователя
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
      // Silent error handling
    }
  }, [username]);

  useEffect(() => {
    if (!username) return;

    fetchPublicChats();
    const interval = setInterval(fetchPublicChats, 300000);
    return () => clearInterval(interval);
  }, [username, fetchPublicChats]);

  // Загрузка чатов при монтировании компонента
  // useEffect(() => {
  //   async function fetchChats() {
  //     const response = await fetch('http://localhost:8000/chats');
  //     const data = await response.json();
  //     setChats(data);
  //   }
  //   fetchChats();
  // }, []);
  const handleSectionChange = (newSection) => {
    // Проверяем доступность секции на основе chat_data
    if (chatData) {
      if (newSection === 'bot' && chatData.ai === false) {
        // AI недоступен, нельзя перейти на bot
        return;
      }
      if ((newSection === 'people' || newSection === 'anon') && !chatData.messengers) {
        // Мессенджеры (публичные и анонимные) недоступны
        return;
      }
      if (newSection === 'settings' && !chatData.settings) {
        // Settings недоступен
        return;
      }
    }
    
    setActiveSection(newSection);
    
    // Сброс выбранного чата при смене секции
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
  
  // Показываем WelcomeScreen если не выбрана секция
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

  return (
    <div className="messenger-container">
      <Navigation
        activeSection={activeSection}
        setActiveSection={handleSectionChange}
        chatData={chatData}
        username={username}
      />
      <div className="messenger-body">
        {!shouldHideList && (
          <div className="messenger-list">
            {renderListPanel()}
          </div>
        )}
        <div className="messenger-chat">
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
      </div>
    </div>
  );
}

export default Messenger;

