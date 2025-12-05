/**
 * Утилита для обработки API запросов с проверкой бана
 */

/**
 * Проверяет, содержит ли ответ сообщение о бане
 * @param {object} data - Объект с данными ответа
 * @returns {boolean}
 */
const isBanMessage = (data) => {
  if (!data || !data.detail) return false;
  const detail = String(data.detail).toLowerCase();
  return detail.includes('заблокирован') || detail.includes('забанен') || detail.includes('banned');
};

/**
 * Выполняет fetch запрос и проверяет статус 403 (бан)
 * @param {string} url - URL для запроса
 * @param {object} options - Опции для fetch
 * @returns {Promise<Response>}
 */
export const fetchWithBanCheck = async (url, options = {}) => {
  const response = await fetch(url, options);
  
  if (response.status === 403) {
    try {
      const clone = response.clone();
      const data = await clone.json();
      if (isBanMessage(data)) {
        window.dispatchEvent(new Event('userBanned'));
      }
    } catch (e) {
      // Ошибка парсинга - не бан
    }
  }
  
  return response;
};

/**
 * Обрабатывает ответ API и проверяет статус 403 на бан
 * @param {Response} response - Ответ от сервера
 * @returns {Promise<boolean>} - true если пользователь забанен
 */
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
      // Ошибка парсинга - не считаем баном
    }
  }
  return false;
};

