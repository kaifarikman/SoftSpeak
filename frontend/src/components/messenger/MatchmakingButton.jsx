import { useState, useEffect, useRef, memo } from 'react';
import { API_URL } from '../../config';
import '../../css/components/MatchmakingButton.css';

// Throttle функция для ограничения частоты обновлений
const throttle = (func, delay) => {
  let timeoutId;
  let lastExecTime = 0;
  return function (...args) {
    const currentTime = Date.now();
    
    if (currentTime - lastExecTime > delay) {
      func(...args);
      lastExecTime = currentTime;
    } else {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        func(...args);
        lastExecTime = Date.now();
      }, delay - (currentTime - lastExecTime));
    }
  };
};

const MatchmakingButton = memo(({ username, onMatchFound }) => {
  const [isSearching, setIsSearching] = useState(false);
  const [queueCount, setQueueCount] = useState(0);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const isConnectingRef = useRef(false);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  
  // Throttled функция для обновления счетчика очереди (максимум раз в 3 секунды)
  const throttledSetQueueCount = useRef(
    throttle((count) => {
      setQueueCount(count);
    }, 3000)
  ).current;

  useEffect(() => {
    // Загружаем начальный статус
    if (username) {
      loadStatus();
    }

    // Очистка при размонтировании
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      isConnectingRef.current = false;
    };
  }, [username]);

  const loadStatus = async () => {
    if (!username) return;
    
    try {
      const response = await fetch(`${API_URL}/matchmaking/status/${username}`);
      if (response.ok) {
        const data = await response.json();
        setIsSearching(data.is_searching);
        setQueueCount(data.queue_count || 0);
      } else {
        // Silent error handling
      }
    } catch (error) {
      // Silent error handling
    }
  };

  const connectWebSocket = () => {
    if (!username || isConnectingRef.current) {
      return;
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    // Закрываем старое соединение, если есть
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    isConnectingRef.current = true;
    setError(null);
    
    // WebSocket для матчинга: /matchmaking/ws/{username}
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/matchmaking/ws/${username}`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      isConnectingRef.current = false;
      reconnectAttemptsRef.current = 0;
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'status') {
          setQueueCount(data.queue_count || 0);
        } else if (data.type === 'searching_started') {
          setIsSearching(true);
          setQueueCount(data.queue_count || 0);
          setError(null);
        } else if (data.type === 'queue_update') {
          // Используем throttled функцию для снижения частоты обновлений UI
          throttledSetQueueCount(data.queue_count || 0);
        } else if (data.type === 'match_found') {
          console.log('WebSocket: матч найден!', data.chat_id);
          console.log('Stopping spinner and calling onMatchFound...');
          
          // Сначала останавливаем спиннер
          setIsSearching(false);
          setQueueCount(0);
          
          // Закрываем WebSocket
          if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
          }
          
          // Затем вызываем колбэк для загрузки чата
          if (onMatchFound && data.chat_id) {
            console.log('Calling onMatchFound with chat_id:', data.chat_id);
            onMatchFound(data.chat_id);
          } else {
            console.warn('onMatchFound callback is missing or chat_id is undefined');
          }
        } else if (data.type === 'search_stopped') {
          setIsSearching(false);
          if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
          }
        } else if (data.type === 'error') {
          setError(data.message || 'Ошибка матчинга');
          setIsSearching(false);
        }
      } catch (err) {
        // Silent error handling
      }
    };

    ws.onerror = (error) => {
      isConnectingRef.current = false;
      setError('Ошибка подключения к серверу');
    };

    ws.onclose = (event) => {
      isConnectingRef.current = false;
      
      // Если это не было намеренное закрытие и мы все еще ищем
      if (event.code !== 1000 && isSearching && reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectAttemptsRef.current++;
        // Экспоненциальная задержка: 5сек, 10сек, 20сек
        const delay = Math.min(5000 * Math.pow(2, reconnectAttemptsRef.current - 1), 20000);
        setTimeout(() => {
          if (isSearching) {
            connectWebSocket();
          }
        }, delay);
      }
    };
  };

  const handleStartMatchmaking = async () => {
    if (!username) {
      setError('Пользователь не найден');
      return;
    }

    setError(null);

    try {
      const response = await fetch(`${API_URL}/matchmaking/start/${username}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setError(null);

        // Если сервер сразу нашел матч, не запускаем поиск и возвращаем чат
        if (data.chat_id) {
          console.log('REST: мгновенный матч найден, чат', data.chat_id);
          setIsSearching(false);
          setQueueCount(data.queue_count || 0);

          // Закрываем активный WS если он вдруг есть
          if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
          }

          if (onMatchFound) {
            onMatchFound(data.chat_id);
          }
          return;
        }

        // В противном случае продолжаем поиск через WebSocket
        setIsSearching(data.is_searching ?? true);
        setQueueCount(data.queue_count || 0);

        if (data.is_searching) {
          connectWebSocket();
        }
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Неизвестная ошибка' }));
        setError(errorData.detail || 'Ошибка начала поиска');
        alert(errorData.detail || 'Ошибка начала поиска');
      }
    } catch (error) {
      setError('Ошибка подключения к серверу');
      alert('Ошибка начала поиска. Проверьте подключение к интернету.');
    }
  };

  const handleStopMatchmaking = async () => {
    if (!username) return;

    try {
      // Отправляем команду остановки через WebSocket, если подключен
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'stop_search' }));
      }

      const response = await fetch(`${API_URL}/matchmaking/stop/${username}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        setIsSearching(false);
        setError(null);
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }
      }
    } catch (error) {
      // Все равно останавливаем локально
      setIsSearching(false);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    }
  };

  if (isSearching) {
    return (
      <div className="matchmaking-container">
        <div className="matchmaking-status">
          <div className="matchmaking-status-line">
            <div className="matchmaking-spinner"></div>
            <p>Ищем собеседника...</p>
          </div>
          <p className="queue-count">
            {queueCount > 0 
              ? `В очереди: ${queueCount} ${queueCount === 1 ? 'человек' : queueCount < 5 ? 'человека' : 'человек'}`
              : 'Ожидание других пользователей...'}
          </p>
          {error && (
            <p className="error-message" style={{ color: '#f44336', fontSize: '12px', marginTop: '5px' }}>
              {error}
            </p>
          )}
        </div>
        <button 
          className="matchmaking-button stop"
          onClick={handleStopMatchmaking}
        >
          Остановить поиск
        </button>
      </div>
    );
  }

  return (
    <div className="matchmaking-container">
      <button 
        className="matchmaking-button start"
        onClick={handleStartMatchmaking}
        disabled={!username}
      >
        Смэтчиться
      </button>
      {error && (
        <p className="error-message" style={{ color: '#f44336', fontSize: '12px', marginTop: '10px' }}>
          {error}
        </p>
      )}
      {queueCount > 0 && !error && (
        <p className="queue-info">
          {queueCount} {queueCount === 1 ? 'человек' : queueCount < 5 ? 'человека' : 'человек'} в очереди
        </p>
      )}
    </div>
  );
});

MatchmakingButton.displayName = 'MatchmakingButton';

export default MatchmakingButton;
