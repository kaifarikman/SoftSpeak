import Navigation from './Navigation';
import ChatList from './ChatList';
import ChatListAnon from './ChatListAnon';
import SettingsList from './SettingsList';

function Sidebar({ activeSection, setActiveSection, chats, selectedChat, setSelectedChat, chatData, username, onChatsUpdate, isNavOpen, onNavClose }) {
  return (
    <div className="sidebar">
      <Navigation
        activeSection={activeSection}
        setActiveSection={setActiveSection}
        chatData={chatData}
        isOpen={isNavOpen}
        onClose={onNavClose}
      />
      
      {activeSection === 'people' && (
        <ChatList
          chats={chats}
          selectedChat={selectedChat}
          setSelectedChat={setSelectedChat}
        />
        
        
      )}
      {activeSection === 'anon' && (
        <ChatListAnon
          chats={chats}
          selectedChat={selectedChat}
          setSelectedChat={setSelectedChat}
          username={username}
          onChatsUpdate={onChatsUpdate}
        />
      )}
      {activeSection === 'settings' && (
        <SettingsList
          settings={chats}
          selectedChat={selectedChat}
          setSelectedChat={setSelectedChat}
        />
      )}
    </div>
  );
}

export default Sidebar;