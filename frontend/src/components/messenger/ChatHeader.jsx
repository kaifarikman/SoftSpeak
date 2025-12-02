function ChatHeader({ chat = {}, actions, onBack, onNameClick, onReportClick }) {
  const fullName = chat.name || 'Диалог';
  const displayName =
    fullName.length > 20 ? `${fullName.slice(0, 20)}…` : fullName;
  const initials = fullName.charAt(0)?.toUpperCase() || 'S';

  return (
    <div className="chat-header">
      <div className="chat-header-info" title={fullName}>
        {onBack && (
          <button className="chat-back-button" onClick={onBack}>
            ← Назад
          </button>
        )}
        <div className="chat-header-avatar placeholder">
          <span>{initials}</span>
        </div>
        <div className="chat-header-text">
          <h2 
            className={onNameClick ? 'chat-header-name-clickable' : ''}
            onClick={onNameClick}
          >
            {displayName}
          </h2>
          {chat.statusText && (
            <p className="chat-header-status">{chat.statusText}</p>
          )}
        </div>
      </div>
      <div className="chat-header-actions">
        {onReportClick && (
          <button
            className="report-button"
            onClick={onReportClick}
            title="Пожаловаться на пользователя"
          >
            ⚠️ Пожаловаться
          </button>
        )}
        {actions}
      </div>
    </div>
  );
}

export default ChatHeader;