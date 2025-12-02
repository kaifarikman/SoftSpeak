function ChatItem({ chat, isSelected, onClick }) {
  const displayName =
    chat.name && chat.name.length > 24
      ? `${chat.name.slice(0, 24)}…`
      : chat.name;

  return (
    <div
      className={`chat-item ${isSelected ? 'selected' : ''}`}
      onClick={onClick}
    >
      <div className="chat-avatar">
        <div className="avatar-placeholder">
          {chat.name && chat.name[0] ? chat.name[0].toUpperCase() : '?'}
        </div>
      </div>
      <div className="chat-info">
        <div className="chat-header-row">
          <span className="chat-name" title={chat.name}>
            {displayName}
          </span>
          <span className="chat-time">{chat.lastMessageTime}</span>
        </div>
        <div className="chat-preview">
          {chat.lastMessage}
        </div>
      </div>
    </div>
  );
}

export default ChatItem;