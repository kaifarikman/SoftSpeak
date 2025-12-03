import { useState } from 'react';

function MessageInput({
  onSend,
  disabled = false,
  placeholder = "Введите сообщение",
}) {
  const [text, setText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
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
        placeholder={placeholder || "Введите сообщение"}
        className="message-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyPress={handleKeyPress}
        disabled={disabled}
      />
      <button type="submit" className="send-button" disabled={disabled || !text.trim()}>
        <span className="send-button-icon"></span>
      </button>
    </form>
  );
}

export default MessageInput;