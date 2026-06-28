import ChatArea from './ChatArea';
import WelcomeScreen from './WelcomeScreen';

export function BotSection({
  showWelcomeScreen,
  email,
  onSelectSection,
  activeChatData,
  chatData,
  onChatDataUpdate,
}) {
  if (showWelcomeScreen) {
    return (
      <WelcomeScreen
        email={email}
        chatData={chatData}
        onSelectSection={onSelectSection}
      />
    );
  }

  return (
    <ChatArea
      selectedChat={activeChatData.selectedChat}
      activeSection="bot"
      chatData={chatData}
      email={email}
      onChatDataUpdate={onChatDataUpdate}
      isStandalone={true}
      onAnonChatExit={() => {}}
      onChatRevealed={() => {}}
      onSectionChange={onSelectSection}
    />
  );
}

function ChatSection({
  activeSection,
  showWelcomeScreen,
  shouldHideList,
  selectedChatAnon,
  email,
  onSelectSection,
  activeChatData,
  chatData,
  onChatDataUpdate,
  onAnonChatExit,
  onChatRevealed,
  onChatsUpdate,
}) {
  return (
    <div className={`messenger-chat ${shouldHideList ? 'messenger-chat-fullwidth' : ''}`}>
      {showWelcomeScreen ? (
        <WelcomeScreen
          email={email}
          chatData={chatData}
          onSelectSection={onSelectSection}
        />
      ) : (
        <ChatArea
          selectedChat={activeChatData.selectedChat}
          activeSection={activeSection}
          chatData={chatData}
          email={email}
          onChatDataUpdate={onChatDataUpdate}
          isStandalone={activeSection === 'anon' && Boolean(selectedChatAnon)}
          onAnonChatExit={onAnonChatExit}
          onChatRevealed={onChatRevealed}
          onChatsUpdate={onChatsUpdate}
          onSectionChange={onSelectSection}
        />
      )}
    </div>
  );
}

export function AnonSection(props) {
  return <ChatSection activeSection="anon" {...props} />;
}

export function PeopleSection(props) {
  return <ChatSection activeSection="people" {...props} />;
}

export function SettingsSection(props) {
  return <ChatSection activeSection="settings" {...props} />;
}
