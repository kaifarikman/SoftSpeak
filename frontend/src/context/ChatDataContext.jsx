import { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { API_URL } from '../config';
import { apiFetch, clearAuthStorage } from '../utils/apiHelper';

const ChatDataContext = createContext();

export const ChatDataProvider = ({ children }) => {
  const [chatData, setChatData] = useState(() => {
    const saved = localStorage.getItem('chat_data');
    return saved ? JSON.parse(saved) : null;
  });

  const updateChatData = useCallback((newData) => {
    setChatData(newData);
    localStorage.setItem('chat_data', JSON.stringify(newData));

    window.dispatchEvent(new Event('chatDataUpdated'));
  }, []);

  const refreshChatData = useCallback(async () => {
    const response = await apiFetch(`${API_URL}/auth/me`);
    if (!response.ok) {
      if (response.status === 401) {
        clearAuthStorage();
        setChatData(null);
      }
      return null;
    }

    const data = await response.json();
    localStorage.setItem('email', data.email);
    localStorage.setItem('nickname', data.nickname);
    updateChatData(data.chat_data);
    if (data.is_banned) {
      window.dispatchEvent(new Event('userBanned'));
    }
    return data;
  }, [updateChatData]);


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
    refreshChatData().catch(() => {});
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('chatDataUpdated', handleChatDataUpdate);
    };
  }, [refreshChatData]);

  return (
    <ChatDataContext.Provider value={{ chatData, updateChatData, refreshChatData }}>
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
