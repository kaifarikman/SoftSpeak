function SettingsItem({ chat, isSelected, onClick }) {
  return (
    <div
      className={`settings-item ${isSelected ? 'selected' : ''}`}
      onClick={onClick}
    >
      
      <div className="setting-info">
          <span className="setting-name">{chat.name}</span>
      </div>
    </div>
  );
}

export default SettingsItem;