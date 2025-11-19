function ChatItemAnon({ onClick }) {
  return (
    <div className="search-button" onClick={OnClick}>
          <span className="search-button-span">Найти собеседника</span>
        </div>
  );
}
function OnClick() {
    console.log("здесь могла быть ваша функция");
}

export default ChatItemAnon;