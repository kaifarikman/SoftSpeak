import { useState, useEffect, useRef, memo } from 'react';
import { API_URL } from '../../config';
import { logError, handleApiError, handleWebSocketError } from '../../utils/errorHandler';
import '../../css/components/MatchmakingButton.css';


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

const MatchmakingButton = memo(({ email, onMatchFound }) => {
  const [isSearching, setIsSearching] = useState(false);
  const [queueCount, setQueueCount] = useState(0);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const isConnectingRef = useRef(false);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  

  const throttledSetQueueCount = useRef(
    throttle((count) => {
      setQueueCount(count);
    }, 3000)
  ).current;

  useEffect(() => {

    if (email) {
      loadStatus();
    }


    return () => {
      if (wsRef.current) {
        try {
          if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
            wsRef.current.close(1000, 'Component unmounting');
          }
        } catch (err) {
          logError(err, 'MatchmakingButton WebSocket cleanup');
        }
        wsRef.current = null;
      }
      isConnectingRef.current = false;
    };
  }, [email]);

  const loadStatus = async () => {
    if (!email) return;
    
    try {
      const response = await fetch(`${API_URL}/matchmaking/status/${email}`);
      if (response.ok) {
        const data = await response.json();
        setIsSearching(data.is_searching);
        setQueueCount(data.queue_count || 0);
      } else {
        await handleApiError(response, 'MatchmakingButton loadStatus');
      }
    } catch (error) {
      logError(error, 'MatchmakingButton loadStatus');
    }
  };

  const connectWebSocket = () => {
    if (!email || isConnectingRef.current) {
      return;
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }


    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    isConnectingRef.current = true;
    setError(null);
    

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = protocol + '//' + host + '/api/matchmaking/ws/' + email;

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

          throttledSetQueueCount(data.queue_count || 0);
        } else if (data.type === 'match_found') {
          console.log('WebSocket: матч найден!', data.chat_id);
          console.log('Stopping spinner and calling onMatchFound...');
          

          setIsSearching(false);
          setQueueCount(0);
          

          if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
          }
          

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
        handleWebSocketError(err, 'MatchmakingButton WebSocket');
      }
    };

    ws.onerror = (error) => {
      isConnectingRef.current = false;
      setError('Ошибка подключения к серверу');
    };

    ws.onclose = (event) => {
      isConnectingRef.current = false;
      

      if (event.code !== 1000 && isSearching && reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectAttemptsRef.current++;

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
    if (!email) {
      setError('Пользователь не найден');
      return;
    }

    setError(null);

    try {
      const response = await fetch(`${API_URL}/matchmaking/start/${email}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setError(null);


        if (data.chat_id) {
          console.log('REST: мгновенный матч найден, чат', data.chat_id);
          setIsSearching(false);
          setQueueCount(data.queue_count || 0);


          if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
          }

          if (onMatchFound) {
            onMatchFound(data.chat_id);
          }
          return;
        }


        setIsSearching(data.is_searching ?? false);
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
    if (!email) return;

    try {

      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'stop_search' }));
      }

      const response = await fetch(`${API_URL}/matchmaking/stop/${email}`, {
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
        disabled={!email}
      >
        Найти собеседника
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
