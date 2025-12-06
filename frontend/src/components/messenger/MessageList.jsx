import { useEffect, useRef } from 'react';
import Message from './Message';

function MessageList({ messages }) {
  const messagesEndRef = useRef(null);
  const messageListRef = useRef(null);
  const previousMessagesCountRef = useRef(0);
  const isInitialLoadRef = useRef(true);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    const currentCount = messages.length;
    const previousCount = previousMessagesCountRef.current;
    
    // Если это первая загрузка (сообщения загружаются сразу), устанавливаем прокрутку в начало
    if (isInitialLoadRef.current && currentCount > 0) {
      isInitialLoadRef.current = false;
      previousMessagesCountRef.current = currentCount;
      // При первой загрузке прокручиваем вверх (к началу), чтобы заголовок был виден
      // Используем requestAnimationFrame для установки прокрутки после рендеринга
      requestAnimationFrame(() => {
        if (messageListRef.current) {
          messageListRef.current.scrollTop = 0;
        }
      });
      return;
    }
    
    // Прокручиваем только если добавлено новое сообщение
    if (currentCount > previousCount) {
      scrollToBottom();
    }
    
    previousMessagesCountRef.current = currentCount;
  }, [messages]);

  // Сбрасываем флаг начальной загрузки при смене чата (когда сообщения очищаются)
  useEffect(() => {
    if (messages.length === 0) {
      isInitialLoadRef.current = true;
      previousMessagesCountRef.current = 0;
    }
  }, [messages.length]);

  return (
    <div className="message-list" ref={messageListRef}>
      {messages.length > 0 ? (
        messages.map(message => (
          <Message key={message.id} message={message} />
        ))
      ) : (
        <div className="empty-messages">
          <p>Начните переписку</p>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
}

export default MessageList;