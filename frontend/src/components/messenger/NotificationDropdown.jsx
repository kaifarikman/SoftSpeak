import { forwardRef } from 'react';
import '../../css/components/NotificationDropdown.css';

const NotificationDropdown = forwardRef(({ notifications, onNotificationClick, onNotificationRemoved }, ref) => {
  const formatTime = (timeString) => {
    const date = new Date(timeString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'только что';
    if (minutes < 60) return `${minutes} мин назад`;
    if (hours < 24) return `${hours} ч назад`;
    if (days < 7) return `${days} дн назад`;
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
  };

  if (notifications.length === 0) {
    return (
      <div ref={ref} className="notification-dropdown">
        <div className="notification-dropdown-header">
          <h3>Уведомления</h3>
        </div>
        <div className="notification-dropdown-empty">
          <p>Нет новых уведомлений</p>
        </div>
      </div>
    );
  }

  return (
    <div ref={ref} className="notification-dropdown">
      <div className="notification-dropdown-header">
        <h3>Уведомления</h3>
        <span className="notification-count">{notifications.length}</span>
      </div>
      <div className="notification-list">
        {notifications.length > 0 ? (
          notifications.map((notification) => (
          <div
            key={notification.chat_id}
            className="notification-item"
            onClick={() => onNotificationClick(notification)}
          >
            <div className="notification-item-header">
              <span className="notification-chat-name">{notification.chat_name}</span>
              <span className="notification-time">{formatTime(notification.last_message_time)}</span>
            </div>
            <div className="notification-item-content">
              <p className="notification-message">{notification.last_message}</p>
              {notification.unread_count > 1 && (
                <span className="notification-unread-count">
                  {notification.unread_count} новых сообщений
                </span>
              )}
            </div>
          </div>
          ))
        ) : (
          <div className="notification-dropdown-empty">
            <p>Нет новых уведомлений</p>
          </div>
        )}
      </div>
    </div>
  );
});

NotificationDropdown.displayName = 'NotificationDropdown';

export default NotificationDropdown;

