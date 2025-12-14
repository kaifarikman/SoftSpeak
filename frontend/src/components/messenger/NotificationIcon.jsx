import { useState, useEffect, useRef, useCallback } from 'react';
import { API_URL } from '../../config';
import NotificationDropdown from './NotificationDropdown';
import '../../css/components/NotificationIcon.css';

function NotificationIcon({ email, onNotificationClick, onNotificationsUpdate }) {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const wsRef = useRef(null);
  const dropdownRef = useRef(null);

  const loadNotifications = useCallback(async () => {
    if (!email) {
      console.log('NotificationIcon: email не передан');
      return;
    }

    try {
      console.log('NotificationIcon: Загрузка уведомлений для', email);
      const response = await fetch(`${API_URL}/notifications/${email}`);
      if (response.ok) {
        const data = await response.json();
        console.log('NotificationIcon: Получены уведомления', data);
        setNotifications(data);
        const total = data.reduce((sum, notif) => sum + notif.unread_count, 0);
        setUnreadCount(total);
        console.log('NotificationIcon: Общее количество непрочитанных', total);
      } else {
        console.error('NotificationIcon: Ошибка ответа', response.status, response.statusText);
      }
    } catch (err) {
      console.error('NotificationIcon: Ошибка загрузки уведомлений:', err);
    }
  }, [email]);

  useEffect(() => {
    console.log('NotificationIcon: useEffect запущен, email:', email);
    
    if (!email) {
      console.log('NotificationIcon: email отсутствует, пропускаем инициализацию');
      return;
    }

    loadNotifications();

    window.notificationUpdateCallback = loadNotifications;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/matchmaking/ws/${email}`;
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      console.log('NotificationIcon: WebSocket для уведомлений подключен для', email);
      loadNotifications();
    };

    wsRef.current.onerror = (error) => {
      console.error('NotificationIcon: WebSocket ошибка:', error);
    };

    wsRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'notification') {
          console.log('NotificationIcon: Получено уведомление через WebSocket:', data);
          setNotifications(prev => {
            const existingIndex = prev.findIndex(n => n.chat_id === data.chat_id);
            let updated;
            
            if (existingIndex >= 0) {
              updated = [...prev];
              updated[existingIndex] = {
                chat_id: data.chat_id,
                chat_name: data.chat_name,
                chat_type: data.chat_type,
                unread_count: data.unread_count,
                last_message: data.last_message,
                last_message_time: new Date().toISOString(),
              };
            } else {
              updated = [{
                chat_id: data.chat_id,
                chat_name: data.chat_name,
                chat_type: data.chat_type,
                unread_count: data.unread_count,
                last_message: data.last_message,
                last_message_time: new Date().toISOString(),
              }, ...prev];
            }
            
            updated.sort((a, b) => new Date(b.last_message_time) - new Date(a.last_message_time));
            return updated;
          });
          
          setTimeout(() => loadNotifications(), 200);
        } else if (data.type === 'ping') {

          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'pong' }));
          }
        } else if (data.type === 'connected') {
          console.log('NotificationIcon: WebSocket подтвердил подключение');
        }
      } catch (err) {
        console.error('Ошибка обработки WebSocket сообщения:', err);
      }
    };

    wsRef.current.onerror = (error) => {
      console.error('NotificationIcon: WebSocket ошибка:', error);
    };

    wsRef.current.onclose = (event) => {
      console.log('NotificationIcon: WebSocket для уведомлений отключен. Код:', event.code, 'Причина:', event.reason);

      if (event.code !== 1000 && email) {
      setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.CLOSED && email) {
          const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
          const host = window.location.host;
          const wsUrl = `${protocol}//${host}/api/matchmaking/ws/${email}`;
          console.log('NotificationIcon: Переподключение WebSocket...');
          wsRef.current = new WebSocket(wsUrl);
          
          wsRef.current.onopen = () => {
            console.log('NotificationIcon: WebSocket переподключен для', email);
            loadNotifications();
          };
          
          wsRef.current.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data);
              if (data.type === 'notification') {
                console.log('NotificationIcon: Получено уведомление через WebSocket:', data);
                setNotifications(prev => {
                  const existingIndex = prev.findIndex(n => n.chat_id === data.chat_id);
                  let updated;
                  
                  if (existingIndex >= 0) {
                    updated = [...prev];
                    updated[existingIndex] = {
                      chat_id: data.chat_id,
                      chat_name: data.chat_name,
                      chat_type: data.chat_type,
                      unread_count: data.unread_count,
                      last_message: data.last_message,
                      last_message_time: new Date().toISOString(),
                    };
                  } else {
                    updated = [{
                      chat_id: data.chat_id,
                      chat_name: data.chat_name,
                      chat_type: data.chat_type,
                      unread_count: data.unread_count,
                      last_message: data.last_message,
                      last_message_time: new Date().toISOString(),
                    }, ...prev];
                  }
                  
                  updated.sort((a, b) => new Date(b.last_message_time) - new Date(a.last_message_time));
                  return updated;
                });
                setTimeout(() => loadNotifications(), 200);
                } else if (data.type === 'ping') {

                  if (wsRef.current?.readyState === WebSocket.OPEN) {
                    wsRef.current.send(JSON.stringify({ type: 'pong' }));
                  }
              }
            } catch (err) {
              console.error('Ошибка обработки WebSocket сообщения:', err);
            }
          };
            
            wsRef.current.onerror = (error) => {
              console.error('NotificationIcon: WebSocket ошибка при переподключении:', error);
          };
        }
        }, 500);
      }
    };

    const interval = setInterval(() => {
      if (email) {
        loadNotifications();
      }
    }, 5000);

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      window.notificationUpdateCallback = null;
      clearInterval(interval);
    };
  }, [email, loadNotifications]);

  useEffect(() => {
    const total = notifications.reduce((sum, notif) => sum + notif.unread_count, 0);
    setUnreadCount(total);
  }, [notifications]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target) && 
          !event.target.closest('.notification-icon')) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const handleToggle = () => {
    setIsOpen(!isOpen);
    if (!isOpen) {
      loadNotifications();
    }
  };

  const handleNotificationClick = (notification) => {
    setIsOpen(false);
    if (onNotificationClick) {
      onNotificationClick(notification);
    }
  };

  const handleNotificationRemoved = (chatId) => {
    setNotifications(prev => prev.filter(n => n.chat_id !== chatId));
    loadNotifications();
  };

  console.log('NotificationIcon: Рендеринг компонента, email =', email);

  return (
    <div className="notification-container" data-testid="notification-container">
      <button
        className="notification-icon"
        onClick={handleToggle}
        title="Уведомления"
        data-testid="notification-button"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M13.73 21a2 2 0 0 1-3.46 0"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        {unreadCount > 0 && (
          <span className="notification-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
        )}
      </button>
      {isOpen && (
        <NotificationDropdown
          ref={dropdownRef}
          notifications={notifications}
          onNotificationClick={handleNotificationClick}
          onNotificationRemoved={handleNotificationRemoved}
        />
      )}
    </div>
  );
}

export default NotificationIcon;

