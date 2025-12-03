/**
 * Утилита для обработки API запросов с проверкой бана
 */

/**
 * Выполняет fetch запрос и проверяет статус 403 (бан)
 * @param {string} url - URL для запроса
 * @param {object} options - Опции для fetch
 * @returns {Promise<Response>}
 */
export const fetchWithBanCheck = async (url, options = {}) => {
  const response = await fetch(url, options);
  
  if (response.status === 403) {
    // Пользователь забанен - отправляем событие
    window.dispatchEvent(new Event('userBanned'));
  }
  
  return response;
};

/**
 * Обрабатывает ответ API и проверяет статус 403
 * @param {Response} response - Ответ от сервера
 * @returns {boolean} - true если пользователь забанен
 */
export const checkBanStatus = (response) => {
  if (response.status === 403) {
    window.dispatchEvent(new Event('userBanned'));
    return true;
  }
  return false;
};

