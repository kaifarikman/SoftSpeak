import { API_URL } from '../config';
import { apiFetch } from './apiHelper';

export const isPushSupported = () => (
  typeof window !== 'undefined'
  && 'serviceWorker' in navigator
  && 'PushManager' in window
  && 'Notification' in window
);

export const urlBase64ToUint8Array = (base64String) => {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const normalized = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');
  const rawData = window.atob(normalized);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
};

export const getPushConfig = async () => {
  const response = await apiFetch(`${API_URL}/notifications/push/config`);
  if (!response.ok) {
    throw new Error('Не удалось получить конфигурацию push-уведомлений');
  }
  return response.json();
};

export const getCurrentPushSubscription = async () => {
  if (!isPushSupported()) {
    return null;
  }
  const registration = await navigator.serviceWorker.ready;
  return registration.pushManager.getSubscription();
};

export const subscribeForPushNotifications = async (email) => {
  if (!isPushSupported()) {
    return { success: false, message: 'Push-уведомления не поддерживаются браузером' };
  }
  const permission = Notification.permission === 'granted'
    ? 'granted'
    : await Notification.requestPermission();
  if (permission !== 'granted') {
    return { success: false, message: 'Разрешение на уведомления отклонено' };
  }

  const { enabled, public_key: publicKey } = await getPushConfig();
  if (!enabled || !publicKey) {
    return { success: false, message: 'Push-уведомления недоступны на сервере' };
  }

  const registration = await navigator.serviceWorker.ready;
  let subscription = await registration.pushManager.getSubscription();
  if (!subscription) {
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    });
  }

  const response = await apiFetch(`${API_URL}/notifications/push/${encodeURIComponent(email)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(subscription.toJSON()),
  });

  if (!response.ok) {
    let message = 'Не удалось подключить push-уведомления';
    try {
      const data = await response.json();
      message = data.detail || data.message || message;
    } catch (error) {
      message = await response.text();
    }
    return { success: false, message };
  }

  return { success: true, subscription };
};

export const unsubscribeFromPushNotifications = async (email) => {
  if (!isPushSupported()) {
    return { success: false, message: 'Push-уведомления не поддерживаются браузером' };
  }

  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.getSubscription();
  if (!subscription) {
    return { success: true, message: 'Подписка уже отключена' };
  }

  const endpoint = subscription.endpoint;
  await subscription.unsubscribe();

  const response = await apiFetch(
    `${API_URL}/notifications/push/${encodeURIComponent(email)}?endpoint=${encodeURIComponent(endpoint)}`,
    { method: 'DELETE' }
  );

  if (!response.ok) {
    let message = 'Не удалось отключить push-уведомления';
    try {
      const data = await response.json();
      message = data.detail || data.message || message;
    } catch (error) {
      message = await response.text();
    }
    return { success: false, message };
  }

  return { success: true };
};
