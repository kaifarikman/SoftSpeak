import { useState } from 'react';

function MessageInput({ onSend, disabled = false, placeholder = "Введите сообщение" }) {
  const [text, setText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (text.trim() && !disabled) {
      onSend(text);
      setText('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !disabled) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form className="message-input-container" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder={disabled ? (placeholder || "Чат недоступен для отправки сообщений") : placeholder}
        className="message-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyPress={handleKeyPress}
        disabled={disabled}
      />
      <button type="submit" className="send-button" disabled={disabled}>
        <span className="send-button-icon"></span>
      </button>
    </form>
  );
}

export default MessageInput;