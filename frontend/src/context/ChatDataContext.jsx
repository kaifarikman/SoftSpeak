import { createContext, useState, useContext, useEffect } from 'react';

const ChatDataContext = createContext();

export const ChatDataProvider = ({ children }) => {
  const [chatData, setChatData] = useState(() => {
    const saved = localStorage.getItem('chat_data');
    return saved ? JSON.parse(saved) : null;
  });

  const updateChatData = (newData) => {
    setChatData(newData);
    localStorage.setItem('chat_data', JSON.stringify(newData));

    window.dispatchEvent(new Event('chatDataUpdated'));
  };


  useEffect(() => {
    const handleStorageChange = (e) => {
      if (e.key === 'chat_data' && e.newValue) {
        try {
          const parsed = JSON.parse(e.newValue);
          setChatData(parsed);
        } catch (err) {
          console.error('Ошибка парсинга chat_data из storage event:', err);
        }
      }
    };


    const handleChatDataUpdate = () => {
      const saved = localStorage.getItem('chat_data');
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          setChatData(parsed);
        } catch (err) {
          console.error('Ошибка парсинга chat_data:', err);
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('chatDataUpdated', handleChatDataUpdate);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('chatDataUpdated', handleChatDataUpdate);
    };
  }, []);

  return (
    <ChatDataContext.Provider value={{ chatData, updateChatData }}>
      {children}
    </ChatDataContext.Provider>
  );
};

export const useChatData = () => {
  const context = useContext(ChatDataContext);
  if (!context) {
    throw new Error('useChatData must be used within a ChatDataProvider');
  }
  return context;
};

