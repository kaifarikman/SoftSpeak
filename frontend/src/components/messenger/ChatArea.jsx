import { useState, useEffect, useRef, memo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import SettingsContent from './SettingsContent';
import UserProfileModal from './UserProfileModal';
import ReportModal from './ReportModal';
import { API_URL, WS_URL } from '../../config';
import { logError, handleApiError, handleWebSocketError } from '../../utils/errorHandler';
import { checkBanStatus } from '../../utils/apiHelper';

const ChatArea = memo(({
  selectedChat,
  activeSection,
  chatData,
  email,
  onChatDataUpdate,
  onChatRevealed,
  onChatsUpdate,
  isStandalone = false,
  onAnonChatExit,
  onSectionChange,
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
  const [showReportModal, setShowReportModal] = useState(false);
  const [chatBlocked, setChatBlocked] = useState(false);
  const [otherUserBanned, setOtherUserBanned] = useState(false);
  const wsRef = useRef(null);
  const anonChatWsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const isConnectingRef = useRef(false);
  const anonChatIdRef = useRef(null);




  useEffect(() => {

    if (activeSection === 'bot' && chatData && chatData.ai === 'start_survey' && email) {
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
  }, [activeSection, chatData?.ai, email]);

  useEffect(() => {
    if (activeSection !== 'anon') {
      setRevealError('');
      setIsRevealing(false);
    }
  }, [activeSection]);


  useEffect(() => {
    if (selectedChat && selectedChat.id && email && (activeSection === 'anon' || activeSection === 'people')) {
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
  }, [activeSection, selectedChat?.id, email]);

  const connectAnonymousChatWebSocket = (chatId) => {
    if (!email || !chatId) return;
    
    if (anonChatWsRef.current && anonChatWsRef.current.readyState === WebSocket.OPEN) {
      return;
    }


    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = protocol + '//' + host + '/api/matchmaking/chat/' + chatId + '/ws/' + email;

    const ws = new WebSocket(wsUrl);
    anonChatWsRef.current = ws;

    ws.onopen = () => {

    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'connected') {

        } else if (data.type === 'new_message') {
          if (anonChatIdRef.current === chatId) {
            const formatted = mapIncomingMessage(data.message);
            upsertMessage(formatted);
          }
        } else if (data.type === 'reveal_request') {
          const systemMessage = {
            id: 'system-reveal-' + Date.now(),
            text: '⚠️ ' + data.message,
            timestamp: new Date().toISOString(),
            isMine: false,
            isSystem: true,
          };
          setMessages(prev => [...prev, systemMessage]);
        } else if (data.type === 'chat_revealed') {

          if (data.both_revealed && onChatRevealed) {
            const formattedChat = {
              id: data.chat_id,
              name: data.other_user.nickname || data.other_user.username,
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

      if (event.code === 4003) {
        window.dispatchEvent(new Event('userBanned'));
      }
    };
  };

  const connectSurveyWebSocket = () => {
    if (!email || isConnectingRef.current) return;
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    isConnectingRef.current = true;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = protocol + '//' + host + '/api/ws/survey/' + email;
    
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
              const response = await fetch(`${API_URL}/chat/data/${email}`);
              if (await checkBanStatus(response)) {
                return;
              }
              if (response.ok) {
                const newChatData = await response.json();
                if (onChatDataUpdate) {
                  onChatDataUpdate(newChatData);
                }

                if (activeSection !== 'bot' && onSectionChange) {
                  onSectionChange('bot');
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

      if (event.code === 4003) {
        window.dispatchEvent(new Event('userBanned'));
        return;
      }
      if (event.code !== 1000 && isSurveyActive) {
        if (!reconnectTimeoutRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null;
            if (isSurveyActive) {
              connectSurveyWebSocket();
            }
          }, 10000);
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


  const loadedMessageIdsRef = useRef(new Set());

  const upsertMessage = useCallback((incoming) => {
    setMessages((prev) => {

      const existsById = prev.some((msg) => msg.id === incoming.id);
      

      const existsByTimestamp = incoming.timestamp && incoming.text
        ? prev.some((msg) => 
            msg.timestamp === incoming.timestamp && 
            msg.text === incoming.text &&
            msg.isMine === incoming.isMine
          )
        : false;
      
      if (existsById) {

        return prev.map((msg) => (msg.id === incoming.id ? incoming : msg));
      }
      
      if (existsByTimestamp) {

        return prev;
      }
      

      if (incoming.id) {
        loadedMessageIdsRef.current.add(incoming.id);
      }
      
      return [...prev, incoming];
    });
  }, []);

  const loadConversationMessages = useCallback(async (chatId) => {
    if (!email) return;

    try {
      const response = await fetch(`${API_URL}/matchmaking/chat/${chatId}/${email}`);
      if (await checkBanStatus(response)) {
        return;
      }
      if (response.ok) {
        const data = await response.json();
        const formattedMessages = data.messages.map(mapIncomingMessage);
        

        if (data.name !== undefined) {
          setChatInfo({
            name: data.name || 'Собеседник',
          });
        }
        

        if (data.is_blocked !== undefined) {
          setChatBlocked(data.is_blocked);
        }
        
        if (data.is_other_user_banned !== undefined) {
          setOtherUserBanned(data.is_other_user_banned);
        }
        

        const seenIds = new Set();
        const seenTimestamps = new Map();
        
        const uniqueMessages = formattedMessages.filter((msg) => {

          if (msg.id) {
            if (seenIds.has(msg.id)) {
              return false;
            }
            seenIds.add(msg.id);
            loadedMessageIdsRef.current.add(msg.id);
          }
          

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
        

        try {
          const readResponse = await fetch(`${API_URL}/matchmaking/chat/${chatId}/read/${email}`, {
            method: 'PUT',
          });
          if (await checkBanStatus(readResponse)) {
            return;
          }
          if (window.notificationUpdateCallback) {
            window.notificationUpdateCallback();
          }
        } catch (readError) {
          logError(readError, 'ChatArea mark messages as read');
        }
      } else {
        setMessages([]);
      }
    } catch (error) {
      setMessages([]);
    }
  }, [email, mapIncomingMessage]);


  useEffect(() => {

    loadedMessageIdsRef.current.clear();

    setChatInfo(null);
    

    if (activeSection === 'bot' && chatData && chatData.ai === 'start_survey') {
      setMessages([]);
      return;
    }

    if (selectedChat && activeSection !== 'settings') {

      if ((activeSection === 'anon' || activeSection === 'people') && selectedChat && selectedChat.id) {
        loadConversationMessages(selectedChat.id);
        return;
      }


      if (activeSection === 'bot' && chatData) {

        if (chatData.ai === true) {
          setMessages([]);
        }

        else if (chatData.ai === false) {
          setMessages([]);
        }

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

      else {
        setMessages([]);
      }
    } else {
      setMessages([]);
    }
  }, [selectedChat, activeSection, chatData?.ai, email, loadConversationMessages]);



  const handleSendMessage = async (text) => {

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



    if (activeSection === 'bot' && chatData) {
      if (chatData.ai === false) {
        return;
      }

      if (Array.isArray(chatData.ai) && chatData.ai.length > 0 && chatData.messengers === true) {
        return;
      }
    }

    const newMessage = {
      id: `temp-${Date.now()}`,
      text: text,
      timestamp: new Date().toISOString(),
      isMine: true,
    };
    setMessages(prev => [...prev, newMessage]);

    if (email) {
      try {
        let response;
        
        if (activeSection === 'bot') {

          response = await fetch(`${API_URL}/chat/message/${email}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
          });
          
          if (await checkBanStatus(response)) {
            setMessages(prev => prev.filter(msg => msg.id !== newMessage.id));
            return;
          }
          
          if (response.ok) {
            const savedMessage = await response.json();
            setMessages(prev => prev.map(msg =>
              msg.id === newMessage.id
                ? { ...msg, id: savedMessage.id, timestamp: savedMessage.created_at }
                : msg
            ));

            setTimeout(async () => {
              try {
                const chatResponse = await fetch(`${API_URL}/chat/data/${email}`);
                if (await checkBanStatus(chatResponse)) {
                  return;
                }
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

          response = await fetch(`${API_URL}/matchmaking/chat/${selectedChat.id}/message/${email}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
          });
          
          if (await checkBanStatus(response)) {
            setMessages(prev => prev.filter(msg => msg.id !== newMessage.id));
            return;
          }
          
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
    localStorage.removeItem('email');
    localStorage.removeItem('nickname');
    localStorage.removeItem('chat_data');
    navigate('/signin');
  };

  const handleRevealChat = async () => {
    if (!selectedChat || !email || isRevealing) {
      return;
    }

    const confirmed = window.confirm('Вы хотите раскрыть свою личность? Собеседник увидит уведомление и сможет согласиться.');
    if (!confirmed) {
      return;
    }

    setIsRevealing(true);
    setRevealError('');

    try {
      const response = await fetch(`${API_URL}/matchmaking/chat/${selectedChat.id}/reveal/${email}`, {
        method: 'POST',
      });
      
      if (await checkBanStatus(response)) {
        return;
      }
      
      let data = null;
      try {
        data = await response.json();
      } catch (parseError) {

        if (response.status === 500) {
          throw new Error('Ошибка сервера при раскрытии профиля. Попробуйте позже.');
        }
        throw new Error('Не удалось обработать ответ сервера');
      }

      if (!response.ok) {

        if (response.status === 500) {
          throw new Error('Ошибка сервера при раскрытии профиля. Попробуйте позже.');
        } else if (response.status === 404) {
          throw new Error('Чат не найден');
        } else if (response.status === 403) {
          throw new Error('Доступ запрещен');
        } else {
        throw new Error((data && data.detail) || 'Не удалось отправить запрос на раскрытие');
        }
      }

      if (!data) {
        throw new Error('Пустой ответ от сервера');
      }

      if (data.status === 'revealed' && data.both_revealed) {

        try {
          const chatResponse = await fetch(`${API_URL}/matchmaking/chat/${selectedChat.id}/${email}`);
          if (chatResponse.ok) {
            const chatData = await chatResponse.json();
            setChatInfo(chatData);
          }
        } catch (reloadError) {
          console.error('Ошибка перезагрузки данных чата:', reloadError);
        }

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
        

        if (onChatsUpdate && activeSection === 'anon') {
          try {
            const chatsResponse = await fetch(`${API_URL}/matchmaking/chats/${email}`);
            if (chatsResponse.ok) {
              const chatsData = await chatsResponse.json();
              const formattedChats = chatsData.map(chat => ({
                id: chat.id,
                name: chat.name || 'Собеседник',
                lastMessage: chat.last_message || '',
                lastMessageTime: chat.last_message_time
                  ? new Date(chat.last_message_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
                  : '',
                unreadCount: chat.unread_count || 0,
              }));
              onChatsUpdate(formattedChats);
            }
          } catch (reloadError) {
            console.error('Ошибка обновления списка чатов после reveal:', reloadError);
          }
        }
      } else if (data.status === 'pending') {
        const systemMessage = {
          id: 'system-pending-' + Date.now(),
          text: '✓ ' + data.message,
          timestamp: new Date().toISOString(),
          isMine: false,
          isSystem: true,
        };
        setMessages(prev => [...prev, systemMessage]);
      }
    } catch (error) {
      console.error('Ошибка при reveal:', error);
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

  const handleOpenReport = useCallback(() => {
    const chatId = selectedChat?.id || (activeSection === 'anon' ? anonChatIdRef.current : null);
    if (chatId) {
      setShowReportModal(true);
    }
  }, [selectedChat, activeSection]);

  const handleCloseReport = useCallback(() => {
    setShowReportModal(false);
  }, []);

  const handleReportSubmitted = useCallback((report) => {
    setChatBlocked(true);
    setShowReportModal(false);
  }, []);


  if (activeSection === 'settings') {
    return (
      <div className="chat-area">
        {selectedChat && <ChatHeader chat={selectedChat} />}
        <SettingsContent
          selectedSetting={selectedChat}
          email={email}
          onChatDataUpdate={onChatDataUpdate}
        />
      </div>
    );
  }

  if (!selectedChat) {

    if (activeSection === 'anon') {
      return (
        <div className="chat-area">
          <div className="empty-state">
            <p>Выберите чат или нажмите "Найти собеседника" чтобы начать общение</p>
          </div>
        </div>
      );
    }
    
    if (activeSection === 'settings') {
      return (
        <div className="chat-area">
          <div className="empty-state">
            <p>Выберите настройку</p>
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
  

  const isBotSurveyCompleted = activeSection === 'bot' && chatData && 
    Array.isArray(chatData.ai) && 
    chatData.ai.length > 0 && 
    chatData.messengers === true;
  

  const hasNoQuestionsError = messages.some(msg => 
    msg.isError && msg.text && msg.text.includes('Нет доступных вопросов для опроса')
  );


  if (activeSection === 'bot' && chatData) {
    console.log('ChatArea bot state:', {
      ai: chatData.ai,
      aiType: typeof chatData.ai,
      isArray: Array.isArray(chatData.ai),
      aiLength: Array.isArray(chatData.ai) ? chatData.ai.length : 0,
      messengers: chatData.messengers,
      isBotSurveyCompleted
    });
  }

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
        onReportClick={
          activeSection !== 'bot' && (selectedChat?.id || (activeSection === 'anon' && anonChatIdRef.current)) 
            ? handleOpenReport 
            : undefined
        }
      />
      {revealError && activeSection === 'anon' && (
        <div className="chat-info-message error">
          {revealError}
        </div>
      )}
      {chatBlocked && (
        <div className="chat-info-message blocked">
          ⚠️ Чат заблокирован из-за жалобы. Отправка сообщений недоступна до рассмотрения администратором.
        </div>
      )}
      {otherUserBanned && !chatBlocked && (
        <div className="chat-info-message banned">
          ⛔ Собеседник заблокирован администратором. Отправка сообщений недоступна.
        </div>
      )}
      <MessageList messages={messages} />
      <MessageInput 
        onSend={handleSendMessage} 
        disabled={
          chatBlocked ||
          otherUserBanned ||
          hasNoQuestionsError ||
          (activeSection === 'bot' && chatData && (
            chatData.ai === false || 
            isBotSurveyCompleted
          ))
        }
        placeholder={
          hasNoQuestionsError
            ? "Нет доступных вопросов для опроса. Обратитесь к администратору."
            : chatBlocked 
            ? "Чат заблокирован. Отправка сообщений недоступна."
            : otherUserBanned
            ? "Собеседник заблокирован. Отправка сообщений недоступна."
            : isBotSurveyCompleted
            ? "Нельзя написать сообщение. Опрос завершен."
            : undefined
        }
      />
      <UserProfileModal
        nickname={profileUsername}
        isOpen={showUserProfile}
        onClose={handleCloseProfile}
      />
      <ReportModal
        chatId={selectedChat?.id || (activeSection === 'anon' ? anonChatIdRef.current : null)}
        isOpen={showReportModal}
        onClose={handleCloseReport}
        onReportSubmitted={handleReportSubmitted}
      />
    </div>
  );
});

ChatArea.displayName = 'ChatArea';

export default ChatArea;
