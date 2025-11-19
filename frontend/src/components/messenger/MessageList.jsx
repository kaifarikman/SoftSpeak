import { useEffect, useRef } from 'react';
import Message from './Message';

function MessageList({ messages }) {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="message-list">
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