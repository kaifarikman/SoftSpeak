import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Navigation from '../components/messenger/Navigation';
import ChatList from '../components/messenger/ChatList';
import ChatListAnon from '../components/messenger/ChatListAnon';
import SettingsList from '../components/messenger/SettingsList';
import BannedOverlay from '../components/BannedOverlay';
import OnboardingOverlay from '../components/messenger/OnboardingOverlay';
import {
  AnonSection,
  BotSection,
  PeopleSection,
  SettingsSection,
} from '../components/messenger/MessengerSections';
import { useChatData } from '../context/ChatDataContext';
import { API_URL } from '../config';
import { logError, handleApiError } from '../utils/errorHandler';
import { apiFetch } from '../utils/apiHelper';
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

  const { chatData, updateChatData, refreshChatData } = useChatData();
  const [activeSection, setActiveSection] = useState('bot');
  const [selectedChatBot, setSelectedChatBot] = useState("SoftSpeak");
  const [selectedChatAnon, setSelectedChatAnon] = useState(null);
  const [selectedChatPeople, setSelectedChatPeople] = useState(null);
  const [selectedChatSettings, setSelectedChatSettings] = useState(null);
  const [isBanned, setIsBanned] = useState(false);
  const [isCheckingBan, setIsCheckingBan] = useState(true);
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    refreshChatData().catch((err) => {
      console.error('Ошибка загрузки данных пользователя:', err);
    });
  }, [refreshChatData]);


  const checkUserStatus = useCallback(async () => {
    const email = localStorage.getItem('email');
    if (!email) return;

    try {
      const response = await apiFetch(`${API_URL}/settings/status/${email}`);
      if (response.ok) {
        const data = await response.json();
        if (data.is_banned) {
          setIsBanned(true);
          window.dispatchEvent(new Event('userBanned'));
          return true;
        } else {
          setIsBanned(false);
          return false;
        }
      } else if (response.status === 403) {

        setIsBanned(true);
        window.dispatchEvent(new Event('userBanned'));
        return true;
      } else {

        setIsBanned(false);
        return false;
      }
    } catch (error) {
      console.error('Ошибка проверки статуса пользователя:', error);

      setIsBanned(false);
      return false;
    }
  }, []);


  useEffect(() => {
    const handleBanned = () => {
      setIsBanned(true);
    };

    window.addEventListener('userBanned', handleBanned);
    return () => window.removeEventListener('userBanned', handleBanned);
  }, []);

  useEffect(() => {
    refreshChatData()
      .then((data) => {
        if (!data) {
          navigate('/signin');
          return;
        }
        return checkUserStatus();
      })
      .finally(() => {
        setIsCheckingBan(false);
      });
    

    const interval = setInterval(() => {
      checkUserStatus();
    }, 10000);
    

    const handleFocus = () => {
      checkUserStatus();
    };
    

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

  useEffect(() => {
    setShowOnboarding(localStorage.getItem('onboarding_done') !== 'true');
  }, []);


  const chatBot = {
    id: 1,
    name: "SoftSpeak",
  };
  const settingsChats = [
    { id: 1, name: "Профиль" },
    { id: 2, name: "Уведомления" },
    { id: 3, name: "Аккаунт" },
  ];
  
  const [chatsPeople, setChatsPeople] = useState([]);
  const [chatsAnon, setChatsAnon] = useState([]);
  const email = localStorage.getItem('email') || '';


  useEffect(() => {
    setChatsPeople([]);
    setChatsAnon([]);
    setSelectedChatAnon(null);
    setSelectedChatPeople(null);
  }, [email]);

  const fetchPublicChats = useCallback(async () => {
    if (!email) return;

    try {
      const response = await apiFetch(`${API_URL}/matchmaking/public-chats/${email}`);
      if (response.status === 403) {

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
  }, [email]);

  useEffect(() => {
    if (!email) return;

    fetchPublicChats();
    const interval = setInterval(fetchPublicChats, 300000);
    return () => clearInterval(interval);
  }, [email, fetchPublicChats]);










  const handleNotificationClick = useCallback(async (notification) => {
    if (!email) return;

    try {
      const response = await apiFetch(`${API_URL}/matchmaking/chat/${notification.chat_id}/read/${email}`, {
        method: 'PUT',
      });
      
      if (response.status === 403) {

        setIsBanned(true);
        return;
      }
      
      if (response.ok) {
        if (notification.chat_type === 'anon') {
          const chatsResponse = await apiFetch(`${API_URL}/matchmaking/chats/${email}`);
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
          const chatsResponse = await apiFetch(`${API_URL}/matchmaking/public-chats/${email}`);
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
  }, [email]);

  const handleSectionChange = (newSection) => {

    if (chatData) {



      if (newSection === 'bot' && chatData.ai === false && (!Array.isArray(chatData.ai) || chatData.ai.length === 0)) {
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
          email={email}
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

  const handleAnonChatRevealed = async (publicChat) => {
    setChatsAnon(prev => prev.filter(chat => chat.id !== publicChat.id));

    setChatsPeople(prev => {
      const filtered = prev.filter(chat => chat.id !== publicChat.id);
      return [publicChat, ...filtered];
    });
    setSelectedChatAnon(null);
    setSelectedChatPeople(publicChat);
    setActiveSection('people');

    try {
      await fetchPublicChats();
      const anonResponse = await apiFetch(`${API_URL}/matchmaking/chats/${email}`);
      if (anonResponse.ok) {
        const anonData = await anonResponse.json();
        const formattedAnon = anonData.map(chat => ({
          id: chat.id,
          name: chat.name,
          lastMessage: chat.last_message || '',
          lastMessageTime: chat.last_message_time
            ? new Date(chat.last_message_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
            : '',
          unreadCount: chat.unread_count || 0,
        }));
        setChatsAnon(formattedAnon);
      }
    } catch (err) {
      logError(err, 'Messenger onChatRevealed refresh');
    }
  };

  const renderSection = () => {
    const commonProps = {
      showWelcomeScreen,
      shouldHideList,
      selectedChatAnon,
      email,
      onSelectSection: handleSectionChange,
      activeChatData,
      chatData,
      onChatDataUpdate: updateChatData,
      onAnonChatExit: () => setSelectedChatAnon(null),
      onChatRevealed: handleAnonChatRevealed,
      onChatsUpdate: setChatsAnon,
    };

    if (activeSection === 'bot') {
      return <BotSection {...commonProps} />;
    }
    if (activeSection === 'anon') {
      return <AnonSection {...commonProps} />;
    }
    if (activeSection === 'people') {
      return <PeopleSection {...commonProps} />;
    }
    return <SettingsSection {...commonProps} />;
  };


  if (isBanned) {
    return <BannedOverlay />;
  }


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
      {showOnboarding && (
        <OnboardingOverlay onFinish={() => setShowOnboarding(false)} />
      )}
      <Navigation
        activeSection={activeSection}
        setActiveSection={handleSectionChange}
        chatData={chatData}
        email={email}
        onNotificationClick={handleNotificationClick}
      />
      <div className="messenger-body">
        {!shouldHideList && (
          <div className="messenger-list">
            {renderListPanel()}
          </div>
        )}
        {renderSection()}
      </div>
    </div>
  );
}

export default Messenger;
