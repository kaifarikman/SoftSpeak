function ChatHeader({ chat, actions }) {
  return (
    <div className="chat-header">
      <div className="chat-header-info">
        <h2>{chat.name}</h2>
      </div>
      <div className="chat-header-actions">
        {actions}
        <button className="menu-button">
          <span className="hamburger-icon"></span>
        </button>
      </div>
    </div>
  );
}

export default ChatHeader;