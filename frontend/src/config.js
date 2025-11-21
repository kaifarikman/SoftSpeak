// API configuration
// В Docker используем относительные пути, так как nginx проксирует запросы
const getApiUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  // Всегда используем относительный путь - nginx проксирует
  return '/api';
};

const getStaticOrigin = () => {
  if (import.meta.env.VITE_STATIC_ORIGIN) {
    return import.meta.env.VITE_STATIC_ORIGIN;
  }
  if (import.meta.env.VITE_API_URL) {
    try {
      const url = new URL(import.meta.env.VITE_API_URL);
      return url.origin;
    } catch {
      // ignore parse errors
    }
  }
  // В режиме разработки по умолчанию используем backend:8000
  if (import.meta.env.DEV) {
    return 'http://localhost:8000';
  }
  return '';
};

const getWsUrl = () => {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  // Используем тот же хост, что и для HTTP
  return `${protocol}//${host}/ws`;
};

export const API_URL = getApiUrl();
export const STATIC_ORIGIN = getStaticOrigin();
export const WS_URL = getWsUrl();

