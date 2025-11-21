function ChatItemAnon({ chat, isSelected, onClick }) {
  const displayName =
    chat.name && chat.name.length > 24
      ? `${chat.name.slice(0, 24)}…`
      : chat.name;

  return (
    <div
      className={`chat-item-anon ${isSelected ? 'selected' : ''}`}
      onClick={onClick}
    >
      <div className="chat-info">
        <div className="chat-header-row">
          <span className="chat-name" title={chat.name}>{displayName}</span>
          <span className="chat-time">{chat.lastMessageTime}</span>
        </div>
        <div className="chat-preview">
          {chat.lastMessage}
        </div>
      </div>
    </div>
  );
}

export default ChatItemAnon;