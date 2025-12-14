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
    

    if (isInitialLoadRef.current && currentCount > 0) {
      isInitialLoadRef.current = false;
      previousMessagesCountRef.current = currentCount;


      requestAnimationFrame(() => {
        if (messageListRef.current) {
          messageListRef.current.scrollTop = 0;
        }
      });
      return;
    }
    

    if (currentCount > previousCount) {
      scrollToBottom();
    }
    
    previousMessagesCountRef.current = currentCount;
  }, [messages]);


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