
import { API_URL } from '../config';

const ACCESS_TOKEN_KEY = 'access_token';

export const getAccessToken = () => localStorage.getItem(ACCESS_TOKEN_KEY);

export const setAccessToken = (token) => {
  if (token) {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
  }
};

export const clearAuthStorage = () => {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem('email');
  localStorage.removeItem('nickname');
  localStorage.removeItem('chat_data');
};

export const refreshAccessToken = async () => {
  const response = await fetch(`${API_URL}/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
  });

  if (!response.ok) {
    clearAuthStorage();
    return null;
  }

  const data = await response.json();
  setAccessToken(data.access_token);
  return data.access_token;
};

export const apiFetch = async (url, options = {}) => {
  const headers = new Headers(options.headers || {});
  const token = getAccessToken();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: options.credentials || 'include',
  });

  if (response.status !== 401) {
    return response;
  }

  const refreshedToken = await refreshAccessToken();
  if (!refreshedToken) {
    return response;
  }

  const retryHeaders = new Headers(options.headers || {});
  retryHeaders.set('Authorization', `Bearer ${refreshedToken}`);
  return fetch(url, {
    ...options,
    headers: retryHeaders,
    credentials: options.credentials || 'include',
  });
};





const isBanMessage = (data) => {
  if (!data || !data.detail) return false;
  const detail = String(data.detail).toLowerCase();
  return detail.includes('заблокирован') || detail.includes('забанен') || detail.includes('banned');
};



export const fetchWithBanCheck = async (url, options = {}) => {
  const response = await apiFetch(url, options);
  
  if (response.status === 403) {
    try {
      const clone = response.clone();
      const data = await clone.json();
      if (isBanMessage(data)) {
        window.dispatchEvent(new Event('userBanned'));
      }
    } catch (e) {

    }
  }
  
  return response;
};



export const checkBanStatus = async (response) => {
  if (response.status === 403) {
    try {
      const clone = response.clone();
      const data = await clone.json();
      if (isBanMessage(data)) {
        window.dispatchEvent(new Event('userBanned'));
        return true;
      }
    } catch (e) {

    }
  }
  return false;
};
