function Message({ message }) {
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  };

  const hasText = Boolean(message.text && message.text.trim().length);
  const renderMedia = () => {
    if (!message.media || !message.media.url) {
      return null;
    }

    if (message.media.type === 'photo') {
      return (
        <div className="message-media photo">
          <img src={message.media.url} alt="Отправленное фото" loading="lazy" />
        </div>
      );
    }

    if (message.media.type === 'video') {
      return (
        <div className="message-media video">
          <video
            src={message.media.url}
            controls
            preload="metadata"
            poster={message.media.previewUrl || undefined}
          />
        </div>
      );
    }

    return null;
  };

  return (
    <div className={`message ${message.isMine ? 'mine' : 'theirs'}`}>
      <div className="message-content">
        {renderMedia()}
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