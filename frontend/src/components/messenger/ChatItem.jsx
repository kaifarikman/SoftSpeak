function ChatItem({ chat, isSelected, onClick }) {
  return (
    <div
      className={`chat-item ${isSelected ? 'selected' : ''}`}
      onClick={onClick}
    >
      <div className="chat-avatar">
        {chat.avatar ? (
          <img src={chat.avatar} alt={chat.name} />
        ) : (
          <div className="avatar-placeholder">
            {chat.name[0].toUpperCase()}
          </div>
        )}
      </div>
      <div className="chat-info">
        <div className="chat-header-row">
          <span className="chat-name">{chat.name}</span>
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