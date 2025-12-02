function Message({ message }) {
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  };

  const hasText = Boolean(message.text && message.text.trim().length);

  return (
    <div className={`message ${message.isMine ? 'mine' : 'theirs'}`}>
      <div className="message-content">
        {hasText && <p>{message.text}</p>}
        <div className="message-footer">
          <span className="message-time">{formatTime(message.timestamp)}</span>
          {message.isMine && message.status && (
            <span className="message-status">
              {message.status === 'sent' && '✓'}
              {message.status === 'delivered' && '✓✓'}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default Message;