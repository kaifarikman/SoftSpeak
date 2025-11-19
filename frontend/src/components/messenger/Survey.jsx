import { useState, useEffect, useRef } from 'react';
import MessageInput from './MessageInput';

function Survey({ username, onComplete }) {
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [currentNumber, setCurrentNumber] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(10);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isCompleted, setIsCompleted] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const isConnectingRef = useRef(false);

  useEffect(() => {
    if (!username) return;

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      isConnectingRef.current = false;
    };
  }, [username]);

  const connectWebSocket = () => {
    if (!username || isConnectingRef.current) return;
    
    // Если уже есть активное соединение, не создаем новое
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    isConnectingRef.current = true;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/survey/${username}`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket подключен');
      setIsLoading(false);
      setError('');
      isConnectingRef.current = false;
      // Сервер автоматически отправит первый вопрос при подключении
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'question') {
          setCurrentQuestion(data.question);
          setCurrentNumber(data.current_question_number);
          setTotalQuestions(data.total_questions);
          setIsLoading(false);
          setError('');
        } else if (data.type === 'survey_completed') {
          // Проверяем, что опрос действительно завершен (есть текущий вопрос или он был)
          // Не показываем "завершен" если пользователь еще не начал опрос
          if (currentQuestion || currentNumber > 0) {
            setIsCompleted(true);
            setIsLoading(false);
            if (onComplete) {
              setTimeout(() => {
                onComplete();
              }, 2000);
            }
            ws.close();
          } else {
            // Если нет текущего вопроса, это ошибка
            setError('Ошибка: получено сообщение о завершении опроса, но опрос не был начат');
            setIsLoading(false);
          }
        } else if (data.type === 'error') {
          setError(data.message || 'Произошла ошибка');
          setIsLoading(false);
        }
      } catch (err) {
        console.error('Ошибка парсинга сообщения:', err);
        setError('Ошибка обработки сообщения');
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket ошибка:', error);
      setError('Ошибка подключения');
      setIsLoading(false);
      isConnectingRef.current = false;
    };

    ws.onclose = (event) => {
      console.log('WebSocket отключен', event.code, event.reason);
      isConnectingRef.current = false;
      
      // Не переподключаемся если:
      // 1. Опрос завершен
      // 2. Закрыто нормально (код 1000)
      // 3. Уже есть запланированное переподключение
      if (isCompleted || event.code === 1000) {
        return;
      }
      
      // Переподключение только если нет активного таймера
      if (!reconnectTimeoutRef.current) {
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectTimeoutRef.current = null;
          if (!isCompleted) {
            connectWebSocket();
          }
        }, 3000);
      }
    };
  };

  const handleAnswer = (answerText) => {
    if (!currentQuestion || !answerText.trim() || isCompleted || !wsRef.current) return;

    if (wsRef.current.readyState === WebSocket.OPEN) {
      setIsLoading(true);
      wsRef.current.send(JSON.stringify({
        type: 'answer',
        question_id: currentQuestion.id,
        answer_text: answerText,
      }));
    } else {
      setError('Соединение не установлено. Попытка переподключения...');
      connectWebSocket();
    }
  };

  if (isLoading) {
    return (
      <div className="chat-area">
        <div className="empty-state">
          <p>Загрузка вопроса...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="chat-area">
        <div className="empty-state">
          <p className="error-text">{error}</p>
        </div>
      </div>
    );
  }

  if (isCompleted || !currentQuestion) {
    return (
      <div className="chat-area">
        <div className="empty-state">
          <p>Опрос завершен! Ваш психологический портрет создан.</p>
          <p>Теперь вы можете искать собеседников.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-area">
      <div className="chat-header">
        <h2>Создание психологического портрета</h2>
        <p>Вопрос {currentNumber} из {totalQuestions}</p>
      </div>
      <div className="message-list">
        <div className="message theirs">
          <div className="message-content">
            <p><strong>{currentQuestion.category.name}</strong></p>
            <p>{currentQuestion.text}</p>
          </div>
        </div>
      </div>
      <MessageInput onSend={handleAnswer} />
    </div>
  );
}

export default Survey;

