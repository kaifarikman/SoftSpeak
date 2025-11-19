function ChatItemAnon({ chat, isSelected, onClick }) {
  return (
    <div
      className={`chat-item-anon ${isSelected ? 'selected' : ''}`}
      onClick={onClick}
    >
      
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

export default ChatItemAnon;