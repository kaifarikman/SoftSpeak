
const isDevelopment = import.meta.env.DEV || import.meta.env.MODE === 'development';

export const logError = (error, context = '') => {
  if (isDevelopment) {
    const errorMessage = error instanceof Error ? error.message : error;
    const contextMsg = context ? `[${context}] ` : '';
    console.error(`${contextMsg}Error:`, errorMessage, error instanceof Error ? error : '');
  }
};

export const handleApiError = async (error, context = '', showNotification = false) => {
  let errorMessage = 'Произошла ошибка';
  
  if (error instanceof Response) {
    try {
      const data = await error.json().catch(() => ({}));
      errorMessage = data.detail || data.message || `HTTP ${error.status}: ${error.statusText}`;
    } catch {
      errorMessage = `HTTP ${error.status}: ${error.statusText}`;
    }
  } else if (error instanceof Error) {
    errorMessage = error.message;
  } else if (typeof error === 'string') {
    errorMessage = error;
  }
  
  logError(errorMessage, context);
  
  if (showNotification && typeof window !== 'undefined') {

    console.warn('User notification:', errorMessage);
  }
  
  return errorMessage;
};

export const handleWebSocketError = (error, context = '') => {
  if (isDevelopment) {
    logError(error, `WebSocket ${context}`);
  }

};

export const handleCriticalError = (error, context = '', onError = null) => {
  const errorMessage = error instanceof Error ? error.message : error;
  logError(errorMessage, `CRITICAL ${context}`);
  
  if (onError && typeof onError === 'function') {
    onError(errorMessage);
  } else if (typeof window !== 'undefined') {

    alert(`Критичная ошибка: ${errorMessage}`);
  }
};

