import { useState, useEffect, useRef, memo } from 'react';
import { useNavigate } from 'react-router-dom';
import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import SettingsContent from './SettingsContent';
import { API_URL, WS_URL } from '../../config';

const ChatArea = memo(({ selectedChat, activeSection, chatData, username, onChatDataUpdate, onChatRevealed }) => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [isSurveyActive, setIsSurveyActive] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [isLoadingAnswer, setIsLoadingAnswer] = useState(false);
  const [isRevealing, setIsRevealing] = useState(false);
  const [revealError, setRevealError] = useState('');
  const wsRef = useRef(null);
  const anonChatWsRef = useRef(null); // WebSocket для анонимного чата
  const reconnectTimeoutRef = useRef(null);
  const isConnectingRef = useRef(false);
  const anonChatIdRef = useRef(null); // ID текущего анонимного чата

  // WebSocket для опроса
  useEffect(() => {
    // Если это опрос, подключаемся к WebSocket
    if (activeSection === 'bot' && chatData && chatData.ai === 'start_survey' && username) {
      setIsSurveyActive(true);
      connectSurveyWebSocket();
      
      return () => {
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
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
          anonChatWsRef.current.close();
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
          // Добавляем новое сообщение в список только если мы все еще в этом чате
          if (anonChatIdRef.current === chatId) {
            const newMessage = {
              id: data.message.id,
              text: data.message.content,
              timestamp: data.message.created_at,
              isMine: false, // Полученное сообщение всегда не мое
            };
            setMessages(prev => {
              // Проверяем, что сообщение еще не добавлено
              const messageExists = prev.some(msg => msg.id === newMessage.id);
              if (!messageExists) {
                return [...prev, newMessage];
              }
              return prev;
            });
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
              avatar: data.other_user.avatar || '',
              lastMessage: data.last_message || '',
              lastMessageTime: data.last_message_time
                ? new Date(data.last_message_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
                : '',
            };
            onChatRevealed(formattedChat);
          }
        }
      } catch (err) {
        // Silent error handling for WebSocket messages
      }
    };

    ws.onerror = (error) => {
      // Silent error handling
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
              // Silent error handling for production
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

  // Загрузка сообщений при выборе чата или смене секции
  useEffect(() => {
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
  }, [selectedChat, activeSection, chatData?.ai, username]);

  const loadConversationMessages = async (chatId) => {
    if (!username) return;

    try {
      const response = await fetch(`${API_URL}/matchmaking/chat/${chatId}/${username}`);
      if (response.ok) {
        const data = await response.json();
        const formattedMessages = data.messages.map(msg => ({
          id: msg.id,
          text: msg.content,
          timestamp: msg.created_at,
          isMine: msg.is_mine,
        }));
        setMessages(formattedMessages);
      } else {
        setMessages([]);
      }
    } catch (error) {
      setMessages([]);
    }
  };

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
                // Silent error handling
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
            // Обновляем временное сообщение на постоянное
            setMessages(prev => prev.map(msg => 
              msg.id === newMessage.id 
                ? { ...msg, id: savedMessage.id, timestamp: savedMessage.created_at }
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
          avatar: data.chat.avatar || '',
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
  const chatHeader = activeSection === 'anon'
    ? { name: 'Собеседник' } 
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
  
  return (
    <div className="chat-area">
      <ChatHeader chat={chatHeader} actions={headerActions} />
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
          (activeSection === 'bot' && isSurveyCompleted)  // Disable input after survey completion
        }
        placeholder={activeSection === 'bot' && isSurveyCompleted ? "Опрос завершен. Чат доступен только для просмотра." : undefined}
      />
    </div>
  );
});

ChatArea.displayName = 'ChatArea';

export default ChatArea;
