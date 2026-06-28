import { useState, useEffect, useRef } from 'react';
import MessageInput from './MessageInput';
import { API_URL } from '../../config';
import { apiFetch } from '../../utils/apiHelper';
import { logError, handleWebSocketError } from '../../utils/errorHandler';
import '../../css/components/TagStep.css';

function Survey({ email, onComplete }) {
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [currentNumber, setCurrentNumber] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(10);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isCompleted, setIsCompleted] = useState(false);
  const [showTagStep, setShowTagStep] = useState(false);
  const [tags, setTags] = useState([]);
  const [selectedTagIds, setSelectedTagIds] = useState([]);
  const [isLoadingTags, setIsLoadingTags] = useState(false);
  const [isSavingTags, setIsSavingTags] = useState(false);
  const [tagError, setTagError] = useState('');
  const [hasLoadedTags, setHasLoadedTags] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const isConnectingRef = useRef(false);
  const hasSurveyStartedRef = useRef(false);

  useEffect(() => {
    if (!email) return;

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        try {
          if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
            wsRef.current.close(1000, 'Component unmounting');
          }
        } catch (err) {
          logError(err, 'Survey WebSocket cleanup');
        }
        wsRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      isConnectingRef.current = false;
      hasSurveyStartedRef.current = false;
    };
  }, [email]);

  const connectWebSocket = () => {
    if (!email || isConnectingRef.current) return;
    

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    isConnectingRef.current = true;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/ws/survey/${email}`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket подключен');
      setIsLoading(false);
      setError('');
      isConnectingRef.current = false;

    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'question') {
          hasSurveyStartedRef.current = true;
          setCurrentQuestion(data.question);
          setCurrentNumber(data.current_question_number);
          setTotalQuestions(data.total_questions);
          setIsLoading(false);
          setError('');
        } else if (data.type === 'survey_completed') {
          if (hasSurveyStartedRef.current) {
            setIsCompleted(true);
            setIsLoading(false);
            setShowTagStep(true);
            ws.close();
          } else {

            setError('Ошибка: получено сообщение о завершении опроса, но опрос не был начат');
            setIsLoading(false);
          }
        } else if (data.type === 'error') {
          setError(data.message || 'Произошла ошибка');
          setIsLoading(false);
        }
      } catch (err) {
        logError(err, 'Survey WebSocket message parsing');
        setError('Ошибка обработки сообщения');
      }
    };

    ws.onerror = (error) => {
      handleWebSocketError(error, 'Survey connection');
      setError('Ошибка подключения');
      setIsLoading(false);
      isConnectingRef.current = false;
    };

    ws.onclose = (event) => {
      console.log('WebSocket отключен', event.code, event.reason);
      isConnectingRef.current = false;
      




      if (isCompleted || event.code === 1000) {
        return;
      }
      

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

  useEffect(() => {
    if (!showTagStep || hasLoadedTags || isLoadingTags) {
      return undefined;
    }

    const loadTags = async () => {
      setIsLoadingTags(true);
      setTagError('');
      try {
        const response = await apiFetch(`${API_URL}/tags`);
        if (!response.ok) {
          throw new Error('Не удалось загрузить интересы');
        }
        const data = await response.json();
        setTags(Array.isArray(data) ? data : []);
      } catch (err) {
        setTagError(err.message || 'Не удалось загрузить интересы');
      } finally {
        setIsLoadingTags(false);
        setHasLoadedTags(true);
      }
    };

    loadTags();
  }, [showTagStep, hasLoadedTags, isLoadingTags]);

  const toggleTag = (tagId) => {
    setSelectedTagIds((prev) => {
      if (prev.includes(tagId)) {
        return prev.filter((id) => id !== tagId);
      }
      if (prev.length >= 5) {
        return prev;
      }
      return [...prev, tagId];
    });
  };

  const handleSubmitTags = async () => {
    if (!email || isSavingTags) {
      return;
    }

    setIsSavingTags(true);
    setTagError('');

    try {
      const response = await apiFetch(`${API_URL}/tags/user/${email}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tag_ids: selectedTagIds }),
      });

      if (!response.ok) {
        let detail = 'Не удалось сохранить интересы';
        try {
          const data = await response.json();
          detail = data.detail || data.message || detail;
        } catch (parseError) {
          // noop
        }
        throw new Error(detail);
      }

      if (onComplete) {
        onComplete();
      }
      setShowTagStep(false);
    } catch (err) {
      setTagError(err.message || 'Не удалось сохранить интересы');
    } finally {
      setIsSavingTags(false);
    }
  };

  if (showTagStep) {
    return (
      <div className="chat-area">
        <div className="tag-step">
          <div className="tag-step-content">
            <p className="tag-step-eyebrow">Анкета завершена</p>
            <h2>Выберите интересы</h2>
            <p className="tag-step-description">
              Отметьте до 5 тем, чтобы поиск собеседника учитывал ваши интересы.
            </p>

            {isLoadingTags ? (
              <div className="tag-step-loading">Загружаем интересы...</div>
            ) : (
              <>
                <div className="tag-grid">
                  {tags.map((tag) => {
                    const isSelected = selectedTagIds.includes(tag.id);
                    const isLocked = !isSelected && selectedTagIds.length >= 5;
                    return (
                      <button
                        key={tag.id}
                        type="button"
                        className={`tag-item ${isSelected ? 'tag-item--selected' : ''}`}
                        onClick={() => toggleTag(tag.id)}
                        disabled={isLocked}
                      >
                        <span className="tag-item-emoji">{tag.emoji}</span>
                        <span>{tag.name}</span>
                      </button>
                    );
                  })}
                </div>

                <p className="tag-step-counter">
                  Выбрано {selectedTagIds.length} из 5
                </p>
              </>
            )}

            {tagError && <p className="tag-step-error">{tagError}</p>}

            <button
              type="button"
              className="tag-step-submit"
              onClick={handleSubmitTags}
              disabled={isLoadingTags || isSavingTags}
            >
              {isSavingTags ? 'Сохраняем...' : 'Продолжить'}
            </button>
          </div>
        </div>
      </div>
    );
  }

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
