/**
 * Утилита для централизованной обработки ошибок
 */

const isDevelopment = import.meta.env.DEV || import.meta.env.MODE === 'development';

/**
 * Логирует ошибку в консоль (только в dev режиме)
 * @param {Error|string} error - Ошибка или сообщение об ошибке
 * @param {string} context - Контекст, где произошла ошибка
 */
export const logError = (error, context = '') => {
  if (isDevelopment) {
    const errorMessage = error instanceof Error ? error.message : error;
    const contextMsg = context ? `[${context}] ` : '';
    console.error(`${contextMsg}Error:`, errorMessage, error instanceof Error ? error : '');
  }
};

/**
 * Обрабатывает ошибку сети или API
 * @param {Error|Response} error - Ошибка или Response объект
 * @param {string} context - Контекст ошибки
 * @param {boolean} showNotification - Показывать ли уведомление пользователю
 * @returns {string|null} - Сообщение об ошибке для отображения или null
 */
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
    // Можно добавить toast уведомления здесь
    console.warn('User notification:', errorMessage);
  }
  
  return errorMessage;
};

/**
 * Обрабатывает ошибку WebSocket
 * @param {Event|Error} error - Ошибка WebSocket
 * @param {string} context - Контекст ошибки
 */
export const handleWebSocketError = (error, context = '') => {
  if (isDevelopment) {
    logError(error, `WebSocket ${context}`);
  }
  // В продакшене можно отправлять ошибки в систему мониторинга
};

/**
 * Обрабатывает критичную ошибку с уведомлением пользователя
 * @param {Error|string} error - Ошибка
 * @param {string} context - Контекст
 * @param {Function} onError - Callback для обработки ошибки
 */
export const handleCriticalError = (error, context = '', onError = null) => {
  const errorMessage = error instanceof Error ? error.message : error;
  logError(errorMessage, `CRITICAL ${context}`);
  
  if (onError && typeof onError === 'function') {
    onError(errorMessage);
  } else if (typeof window !== 'undefined') {
    // Показываем alert для критичных ошибок
    alert(`Критичная ошибка: ${errorMessage}`);
  }
};

