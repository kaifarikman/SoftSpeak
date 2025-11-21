import { resolveStaticUrl } from '../../utils/url';

function ChatHeader({ chat = {}, actions, onBack }) {
  const fullName = chat.name || 'Диалог';
  const displayName =
    fullName.length > 20 ? `${fullName.slice(0, 20)}…` : fullName;
  const avatarSrc = chat.avatar ? resolveStaticUrl(chat.avatar) : null;
  const initials = fullName.charAt(0)?.toUpperCase() || 'S';

  return (
    <div className="chat-header">
      <div className="chat-header-info" title={fullName}>
        {onBack && (
          <button className="chat-back-button" onClick={onBack}>
            ← Назад
          </button>
        )}
        <div className={`chat-header-avatar ${avatarSrc ? '' : 'placeholder'}`}>
          {avatarSrc ? (
            <img src={avatarSrc} alt={fullName} />
          ) : (
            <span>{initials}</span>
          )}
        </div>
        <div className="chat-header-text">
          <h2>{displayName}</h2>
          {chat.statusText && (
            <p className="chat-header-status">{chat.statusText}</p>
          )}
        </div>
      </div>
      <div className="chat-header-actions">{actions}</div>
    </div>
  );
}

export default ChatHeader;