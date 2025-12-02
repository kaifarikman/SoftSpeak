import { useState, useEffect, useRef, memo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import SettingsContent from './SettingsContent';
import UserProfileModal from './UserProfileModal';
import { API_URL, WS_URL } from '../../config';
import { logError, handleApiError, handleWebSocketError } from '../../utils/errorHandler';

const ChatArea = memo(({
  selectedChat,
  activeSection,
  chatData,
  username,
  onChatDataUpdate,
  onChatRevealed,
  isStandalone = false,
  onAnonChatExit,
}) => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [isSurveyActive, setIsSurveyActive] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [isLoadingAnswer, setIsLoadingAnswer] = useState(false);
  const [isRevealing, setIsRevealing] = useState(false);
  const [revealError, setRevealError] = useState('');
  const [chatInfo, setChatInfo] = useState(null);
  const [showUserProfile, setShowUserProfile] = useState(false);
  const [profileUsername, setProfileUsername] = useState(null);
  const wsRef = useRef(null);
  const anonChatWsRef = useRef(null); // WebSocket для анонимного чата
  const reconnectTimeoutRef = useRef(null);
  const isConnectingRef = useRef(false);
  const anonChatIdRef = useRef(null); // ID текущего анонимного чата

  // helper functions defined above

  // WebSocket для опроса
  useEffect(() => {
    // Если это опрос, подключаемся к WebSocket
    if (activeSection === 'bot' && chatData && chatData.ai === 'start_survey' && username) {
      setIsSurveyActive(true);
      connectSurveyWebSocket();
      
      return () => {
        if (wsRef.current) {
          try {
            if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
              wsRef.current.close(1000, 'Component unmounting');
            }
          } catch (err) {
            logError(err, 'ChatArea survey WebSocket cleanup');
          }
          wsRef.current = null;
        }
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
        isConnectingRef.current = false;
      };
    } else {
      setIsSurveyActive(false);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    }
  }, [activeSection, chatData?.ai, username]);

  useEffect(() => {
    if (activeSection !== 'anon') {
      setRevealError('');
      setIsRevealing(false);
    }
  }, [activeSection]);

  // WebSocket для анонимного и публичного чата
  useEffect(() => {
    if (selectedChat && selectedChat.id && username && (activeSection === 'anon' || activeSection === 'people')) {
      connectAnonymousChatWebSocket(selectedChat.id);
      anonChatIdRef.current = selectedChat.id;

      return () => {
        if (anonChatWsRef.current) {
          try {
            if (anonChatWsRef.current.readyState === WebSocket.OPEN || anonChatWsRef.current.readyState === WebSocket.CONNECTING) {
              anonChatWsRef.current.close(1000, 'Component unmounting');
            }
          } catch (err) {
            logError(err, 'ChatArea anonymous chat WebSocket cleanup');
          }
          anonChatWsRef.current = null;
        }
        anonChatIdRef.current = null;
      };
    } else {
      if (anonChatWsRef.current) {
        anonChatWsRef.current.close();
        anonChatWsRef.current = null;
      }
      anonChatIdRef.current = null;
    }
  }, [activeSection, selectedChat?.id, username]);

  const connectAnonymousChatWebSocket = (chatId) => {
    if (!username || !chatId) return;
    
    if (anonChatWsRef.current && anonChatWsRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    // WebSocket для анонимного чата: /matchmaking/chat/{chat_id}/ws/{username}
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/matchmaking/chat/${chatId}/ws/${username}`;

    const ws = new WebSocket(wsUrl);
    anonChatWsRef.current = ws;

    ws.onopen = () => {
      // WebSocket connected successfully
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'connected') {
          // Connected to chat successfully
        } else if (data.type === 'new_message') {
          if (anonChatIdRef.current === chatId) {
            const formatted = mapIncomingMessage(data.message);
            upsertMessage(formatted);
          }
        } else if (data.type === 'reveal_request') {
          // Собеседник хочет раскрыться
          const systemMessage = {
            id: `system-reveal-${Date.now()}`,
            text: '⚠️ ' + data.message,
            timestamp: new Date().toISOString(),
            isMine: false,
            isSystem: true,
          };
          setMessages(prev => [...prev, systemMessage]);
        } else if (data.type === 'chat_revealed') {
          // Чат раскрыт - переводим в публичный
          if (data.both_revealed && onChatRevealed) {
            const formattedChat = {
              id: data.chat_id,
              name: data.other_user.username,
              lastMessage: data.last_message || '',
              lastMessageTime: data.last_message_time
                ? new Date(data.last_message_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
                : '',
            };
            onChatRevealed(formattedChat);
          }
        }
      } catch (err) {
        handleWebSocketError(err, 'ChatArea anonymous chat message');
      }
    };

    ws.onerror = (error) => {
      handleWebSocketError(error, 'ChatArea anonymous chat connection');
    };

    ws.onclose = (event) => {
      anonChatWsRef.current = null;
    };
  };

  const connectSurveyWebSocket = () => {
    if (!username || isConnectingRef.current) return;
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    isConnectingRef.current = true;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/survey/${username}`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      isConnectingRef.current = false;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'question') {
          const questionMessage = {
            id: `q-${Date.now()}`,
            text: data.question?.text || data.text,
            timestamp: new Date().toISOString(),
            isMine: false,
          };
          setMessages(prev => [...prev, questionMessage]);
          setCurrentQuestion(data);
          setIsLoadingAnswer(false);
        } else if (data.type === 'answer_history') {
          const answerMessage = {
            id: `history-a-${Date.now()}`,
            text: data.answer_text,
            timestamp: data.created_at,
            isMine: true,
          };
          setMessages(prev => [...prev, answerMessage]);
        } else if (data.type === 'processing') {
          const processingMessage = {
            id: `processing-${Date.now()}`,
            text: data.message || 'Обрабатываем ваши ответы...',
            timestamp: new Date().toISOString(),
            isMine: false,
            isProcessing: true,
          };
          setMessages(prev => [...prev, processingMessage]);
          setIsLoadingAnswer(false);
        } else if (data.type === 'survey_completed') {
          const completedMessage = {
            id: `completed-${Date.now()}`,
            text: data.message || 'Спасибо! Опрос завершен.',
            timestamp: new Date().toISOString(),
            isMine: false,
          };
          setMessages(prev => [...prev, completedMessage]);
          setIsSurveyActive(false);
          setCurrentQuestion(null);
          setIsLoadingAnswer(false);
          
          setTimeout(async () => {
            try {
              const response = await fetch(`${API_URL}/chat/data/${username}`);
              if (response.ok) {
                const newChatData = await response.json();
                if (onChatDataUpdate) {
                  onChatDataUpdate(newChatData);
                }
              }
            } catch (err) {
              logError(err, 'ChatArea survey completion chat data update');
            }
          }, 2000);
        } else if (data.type === 'error') {
          const errorMessage = {
            id: `error-${Date.now()}`,
            text: `Ошибка: ${data.message}`,
            timestamp: new Date().toISOString(),
            isMine: false,
            isError: true,
          };
          setMessages(prev => [...prev, errorMessage]);
          setIsLoadingAnswer(false);
        }
      } catch (err) {
        console.error('Ошибка парсинга сообщения:', err);
      }
    };

    ws.onerror = (error) => {
      isConnectingRef.current = false;
    };

    ws.onclose = (event) => {
      isConnectingRef.current = false;
      if (event.code !== 1000 && isSurveyActive) {
        if (!reconnectTimeoutRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null;
            if (isSurveyActive) {
              connectSurveyWebSocket();
            }
          }, 10000); // Увеличиваем интервал до 10 секунд
        }
      }
    };
  };

  const mapIncomingMessage = useCallback((payload) => {
    return {
      id: payload.id,
      text: payload.content || '',
      timestamp: payload.created_at,
      isMine: typeof payload.is_mine === 'boolean' ? payload.is_mine : false,
    };
  }, []);

  // Set для отслеживания уже загруженных ID сообщений
  const loadedMessageIdsRef = useRef(new Set());

  const upsertMessage = useCallback((incoming) => {
    setMessages((prev) => {
      // Проверяем по ID
      const existsById = prev.some((msg) => msg.id === incoming.id);
      
      // Проверяем по timestamp и тексту (для дедупликации без ID)
      const existsByTimestamp = incoming.timestamp && incoming.text
        ? prev.some((msg) => 
            msg.timestamp === incoming.timestamp && 
            msg.text === incoming.text &&
            msg.isMine === incoming.isMine
          )
        : false;
      
      if (existsById) {
        // Обновляем существующее сообщение
        return prev.map((msg) => (msg.id === incoming.id ? incoming : msg));
      }
      
      if (existsByTimestamp) {
        // Дубликат по timestamp, пропускаем
        return prev;
      }
      
      // Добавляем ID в Set отслеживания
      if (incoming.id) {
        loadedMessageIdsRef.current.add(incoming.id);
      }
      
      return [...prev, incoming];
    });
  }, []);

  const loadConversationMessages = useCallback(async (chatId) => {
    if (!username) return;

    try {
      const response = await fetch(`${API_URL}/matchmaking/chat/${chatId}/${username}`);
      if (response.ok) {
        const data = await response.json();
        const formattedMessages = data.messages.map(mapIncomingMessage);
        
        // Обновляем информацию о чате (аватар, имя) из ответа API
        if (data.name !== undefined) {
          setChatInfo({
            name: data.name || 'Собеседник',
          });
        }
        
        // Дедупликация при загрузке: используем Set для отслеживания ID
        const seenIds = new Set();
        const seenTimestamps = new Map(); // timestamp -> Set of texts
        
        const uniqueMessages = formattedMessages.filter((msg) => {
          // Проверка по ID
          if (msg.id) {
            if (seenIds.has(msg.id)) {
              return false;
            }
            seenIds.add(msg.id);
            loadedMessageIdsRef.current.add(msg.id);
          }
          
          // Проверка по timestamp и тексту (для сообщений без ID)
          if (msg.timestamp && msg.text) {
            const key = `${msg.timestamp}_${msg.isMine}`;
            if (!seenTimestamps.has(key)) {
              seenTimestamps.set(key, new Set());
            }
            const texts = seenTimestamps.get(key);
            if (texts.has(msg.text)) {
              return false;
            }
            texts.add(msg.text);
          }
          
          return true;
        });
        
        setMessages(uniqueMessages);
        
        // Помечаем сообщения как прочитанные после загрузки
        try {
          await fetch(`${API_URL}/matchmaking/chat/${chatId}/read/${username}`, {
            method: 'PUT',
          });
        } catch (readError) {
          logError(readError, 'ChatArea mark messages as read');
        }
      } else {
        setMessages([]);
      }
    } catch (error) {
      setMessages([]);
    }
  }, [username, mapIncomingMessage]);

  // Загрузка сообщений при выборе чата или смене секции
  useEffect(() => {
    // Очищаем Set отслеживания при смене чата
    loadedMessageIdsRef.current.clear();
    // Сбрасываем информацию о чате при смене чата
    setChatInfo(null);
    
    // Если это опрос, не загружаем сообщения из БД
    if (activeSection === 'bot' && chatData && chatData.ai === 'start_survey') {
      setMessages([]);
      return;
    }

    if (selectedChat && activeSection !== 'settings') {
      // Загрузка сообщений для анонимного или публичного чата
      if ((activeSection === 'anon' || activeSection === 'people') && selectedChat && selectedChat.id) {
        loadConversationMessages(selectedChat.id);
        return;
      }

      // Если это AI чат (bot), используем данные из chatData
      if (activeSection === 'bot' && chatData) {
        // Если ai = true, это новый чат, сообщений нет
        if (chatData.ai === true) {
          setMessages([]);
        }
        // Если ai = false, AI недоступен (не должно быть здесь, но на всякий случай)
        else if (chatData.ai === false) {
          setMessages([]);
        }
        // Если ai = массив сообщений, преобразуем их в формат фронтенда
        else if (Array.isArray(chatData.ai)) {
          const formattedMessages = chatData.ai.map(msg => ({
            id: msg.id,
            text: msg.content,
            timestamp: msg.created_at,
            isMine: msg.is_from_user
          }));
          setMessages(formattedMessages);
        }
      }
      // Для других секций (people) загружаем из API
      else {
        setMessages([]);
      }
    } else {
      setMessages([]);
    }
  }, [selectedChat, activeSection, chatData?.ai, username, loadConversationMessages]);

  // loadConversationMessages moved above with useCallback

  const handleSendMessage = async (text) => {
    // Если это опрос, отправляем ответ через WebSocket
    if (isSurveyActive && currentQuestion) {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        const userMessage = {
          id: `a-${Date.now()}`,
          text: text,
          timestamp: new Date().toISOString(),
          isMine: true,
        };
        setMessages(prev => [...prev, userMessage]);
        setIsLoadingAnswer(true);
        
        wsRef.current.send(JSON.stringify({
          type: 'answer',
          answer_text: text,
          question_id: currentQuestion.question?.id || currentQuestion.question_id
        }));
        
        setCurrentQuestion(null);
      }
      return;
    }
    
    if (!selectedChat) return;

    // Сообщение для AI чата или анонимного чата отключено после завершения опроса
    if (activeSection === 'bot' && chatData && (chatData.ai === false || Array.isArray(chatData.ai))) {
      return;
    }

    const newMessage = {
      id: `temp-${Date.now()}`,
      text: text,
      timestamp: new Date().toISOString(),
      isMine: true,
    };
    setMessages(prev => [...prev, newMessage]);

    if (username) {
      try {
        let response;
        
        if (activeSection === 'bot') {
          // AI chat
          response = await fetch(`${API_URL}/chat/message/${username}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
          });
          
          if (response.ok) {
            const savedMessage = await response.json();
            setMessages(prev => prev.map(msg =>
              msg.id === newMessage.id
                ? { ...msg, id: savedMessage.id, timestamp: savedMessage.created_at }
                : msg
            ));

            setTimeout(async () => {
              try {
                const chatResponse = await fetch(`${API_URL}/chat/data/${username}`);
                if (chatResponse.ok) {
                  const newChatData = await chatResponse.json();
                  if (onChatDataUpdate) {
                    onChatDataUpdate(newChatData);
                  }
                }
              } catch (err) {
                logError(err, 'ChatArea send message');
              }
            }, 1000);
          } else {
            setMessages(prev => prev.filter(msg => msg.id !== newMessage.id));
          }
        } else if ((activeSection === 'anon' || activeSection === 'people') && selectedChat && selectedChat.id) {
          // Anonymous или публичный чат
          response = await fetch(`${API_URL}/matchmaking/chat/${selectedChat.id}/message/${username}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
          });
          
          if (response.ok) {
            const savedMessage = await response.json();
            const formatted = mapIncomingMessage(savedMessage);
            setMessages(prev => prev.map(msg => 
              msg.id === newMessage.id 
                ? formatted
                : msg
            ));
          } else {
            setMessages(prev => prev.filter(msg => msg.id !== newMessage.id));
          }
        }
      } catch (error) {
        setMessages(prev => prev.filter(msg => msg.id !== newMessage.id));
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('username');
    localStorage.removeItem('chat_data');
    navigate('/signin');
  };

  const handleRevealChat = async () => {
    if (!selectedChat || !username || isRevealing) {
      return;
    }

    const confirmed = window.confirm('Вы хотите раскрыть свою личность? Собеседник увидит уведомление и сможет согласиться.');
    if (!confirmed) {
      return;
    }

    setIsRevealing(true);
    setRevealError('');

    try {
      const response = await fetch(`${API_URL}/matchmaking/chat/${selectedChat.id}/reveal/${username}`, {
        method: 'POST',
      });
      const data = await response.json().catch(() => null);

      if (!response.ok || !data) {
        throw new Error((data && data.detail) || 'Не удалось отправить запрос на раскрытие');
      }

      if (data.status === 'revealed' && data.both_revealed) {
        // Оба согласны - чат переходит в публичный
        const formattedChat = {
          id: data.chat.id,
          name: data.chat.name,
          lastMessage: data.chat.last_message || '',
          lastMessageTime: data.chat.last_message_time
            ? new Date(data.chat.last_message_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
            : '',
        };

        if (onChatRevealed) {
          onChatRevealed(formattedChat);
        }
      } else if (data.status === 'pending') {
        // Ожидаем согласия другого пользователя
        const systemMessage = {
          id: `system-pending-${Date.now()}`,
          text: '✓ ' + data.message,
          timestamp: new Date().toISOString(),
          isMine: false,
          isSystem: true,
        };
        setMessages(prev => [...prev, systemMessage]);
      }
    } catch (error) {
      setRevealError(error.message || 'Не удалось отправить запрос на раскрытие');
    } finally {
      setIsRevealing(false);
    }
  };

  const handleOpenProfile = useCallback(() => {
    if (activeSection === 'people' && selectedChat?.name) {
      setProfileUsername(selectedChat.name);
      setShowUserProfile(true);
    }
  }, [activeSection, selectedChat]);

  const handleCloseProfile = useCallback(() => {
    setShowUserProfile(false);
    setProfileUsername(null);
  }, []);

  // Special handling for settings section
  if (activeSection === 'settings') {
    return (
      <div className="chat-area">
        {selectedChat && <ChatHeader chat={selectedChat} />}
        <SettingsContent
          selectedSetting={selectedChat}
          username={username}
          onChatDataUpdate={onChatDataUpdate}
        />
      </div>
    );
  }

  if (!selectedChat) {
    // If it's an anonymous chat and no chat is selected, show a specific empty state
    if (activeSection === 'anon') {
      return (
        <div className="chat-area">
          <div className="empty-state">
            <p>Выберите чат или нажмите "Найти собеседника" чтобы начать общение</p>
          </div>
        </div>
      );
    }
    
    return (
      <div className="chat-area">
        <div className="empty-state">
          <p>Выберите чат, чтобы начать общение</p>
        </div>
      </div>
    );
  }

  const isSurveyCompleted = chatData && Array.isArray(chatData.ai) && chatData.ai.length > 0;
  
  // Use a special header for anonymous chats
  const anonDisplayName = activeSection === 'anon'
    ? (chatInfo?.name || selectedChat?.name || 'Собеседник')
    : null;

  const chatHeader = activeSection === 'anon'
    ? { name: anonDisplayName }
    : selectedChat;

  const headerActions = activeSection === 'anon' ? (
    <button
      className="reveal-button"
      onClick={handleRevealChat}
      disabled={isRevealing}
    >
      {isRevealing ? 'Раскрываем...' : 'Раскрыться'}
    </button>
  ) : null;

  const showAnonBackButton = activeSection === 'anon' && typeof onAnonChatExit === 'function' && isStandalone;
  const chatAreaClass = `chat-area ${isStandalone ? 'chat-area-standalone' : ''}`;
  const isPublicChat = activeSection === 'people';
  
  return (
    <div className={chatAreaClass}>
      <ChatHeader
        chat={chatHeader}
        actions={headerActions}
        onBack={showAnonBackButton ? onAnonChatExit : undefined}
        onNameClick={isPublicChat ? handleOpenProfile : undefined}
      />
      {revealError && activeSection === 'anon' && (
        <div className="chat-info-message error">
          {revealError}
        </div>
      )}
      <MessageList messages={messages} />
      <MessageInput 
        onSend={handleSendMessage} 
        disabled={
          (activeSection === 'bot' && chatData && chatData.ai === false) ||
          (activeSection === 'bot' && isSurveyCompleted)
        }
        placeholder={activeSection === 'bot' && isSurveyCompleted ? "Опрос завершен. Чат доступен только для просмотра." : undefined}
      />
      <UserProfileModal
        username={profileUsername}
        isOpen={showUserProfile}
        onClose={handleCloseProfile}
      />
    </div>
  );
});

ChatArea.displayName = 'ChatArea';

export default ChatArea;
