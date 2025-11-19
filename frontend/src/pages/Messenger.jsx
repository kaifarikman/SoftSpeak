import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/messenger/Sidebar';
import ChatArea from '../components/messenger/ChatArea';
import WelcomeScreen from '../components/messenger/WelcomeScreen';
import HamburgerMenu from '../components/messenger/HamburgerMenu';
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
import '../css/components/Sidebar.css';
import '../css/components/SettingsContent.css';
import '../css/components/WelcomeScreen.css';
import '../css/components/HamburgerMenu.css';

function Messenger() {
  const navigate = useNavigate();
  // Используем Context API вместо прямого доступа к localStorage
  const { chatData, updateChatData } = useChatData();
  const [activeSection, setActiveSection] = useState(null); // bot, anon, people, settings, null = welcome
  const [selectedChatBot, setSelectedChatBot] = useState("SoftSpeak");
  const [selectedChatAnon, setSelectedChatAnon] = useState(null);
  const [selectedChatPeople, setSelectedChatPeople] = useState(null);
  const [selectedChatSettings, setSelectedChatSettings] = useState(null);
  const [isNavOpen, setIsNavOpen] = useState(false);

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
    setIsNavOpen(false); // Закрываем меню на мобильных после выбора
    
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

  const toggleNav = () => {
    setIsNavOpen(!isNavOpen);
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
  
  // Показываем WelcomeScreen если не выбрана секция
  const showWelcomeScreen = !activeSection;

  return (
    <div className="messenger-container">
      <HamburgerMenu isOpen={isNavOpen} toggleMenu={toggleNav} />
      
      <Sidebar
        activeSection={activeSection}
        setActiveSection={handleSectionChange}
        chats={activeChatData.chats}
        selectedChat={activeChatData.selectedChat}
        setSelectedChat={activeChatData.setSelectedChat}
        chatData={chatData}
        username={username}
        onChatsUpdate={setChatsAnon}
        isNavOpen={isNavOpen}
        onNavClose={() => setIsNavOpen(false)}
      />
      {showWelcomeScreen ? (
        <WelcomeScreen username={username} />
      ) : (
        <ChatArea
          selectedChat={activeChatData.selectedChat}
          activeSection={activeSection}
          chatData={chatData}
          username={username}
          onChatDataUpdate={updateChatData}
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
  );
}

export default Messenger;

