// API configuration
// В Docker используем относительные пути, так как nginx проксирует запросы
const getApiUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  // Всегда используем относительный путь - nginx проксирует
  return '/api';
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
export const WS_URL = getWsUrl();

