/**
 * Форматирует ошибки валидации Pydantic в читаемый текст
 * @param {Object} errorData - Объект ошибки от API
 * @returns {string} - Отформатированное сообщение об ошибке
 */
export function formatApiError(errorData) {
  // Если detail - строка, возвращаем её как есть
  if (typeof errorData.detail === 'string') {
    return errorData.detail;
  }

  // Если detail - массив (ошибки валидации Pydantic)
  if (Array.isArray(errorData.detail)) {
    const errors = errorData.detail.map(error => {
      const field = error.loc && error.loc.length > 0 
        ? error.loc[error.loc.length - 1] 
        : 'поле';
      
      // Преобразуем название поля в читаемый формат
      const fieldName = getFieldName(field);
      
      // Преобразуем сообщение об ошибке в русский текст
      const message = getErrorMessage(error.type, error.msg, fieldName);
      
      return message;
    });

    // Объединяем все ошибки в одну строку
    return errors.join('. ');
  }

  // Если detail - объект, но не массив
  if (errorData.detail && typeof errorData.detail === 'object') {
    return JSON.stringify(errorData.detail);
  }

  // Если detail отсутствует, возвращаем общее сообщение
  return 'Произошла ошибка при обработке запроса';
}

/**
 * Преобразует техническое название поля в читаемое
 * @param {string} field - Техническое название поля
 * @returns {string} - Читаемое название поля
 */
function getFieldName(field) {
  const fieldNames = {
    'email': 'Email',
    'password': 'Пароль',
    'nickname': 'Никнейм',
    'username': 'Логин',
    'code': 'Код подтверждения',
    'login': 'Логин',
  };

  return fieldNames[field] || field;
}

/**
 * Преобразует тип ошибки и сообщение в читаемый русский текст
 * @param {string} errorType - Тип ошибки (missing, value_error, etc.)
 * @param {string} errorMsg - Сообщение об ошибке от Pydantic
 * @param {string} fieldName - Название поля
 * @returns {string} - Читаемое сообщение об ошибке
 */
function getErrorMessage(errorType, errorMsg, fieldName) {
  // Преобразуем errorMsg в строку, если это не строка (защита от объектов, null, undefined)
  const errorMsgStr = errorMsg && typeof errorMsg === 'string' ? errorMsg : String(errorMsg || '');
  
  // Если сообщение уже на русском (пришло с бэкенда), возвращаем его как есть
  if (errorMsgStr && 
      (errorMsgStr.includes('Слишком длинный') || 
       errorMsgStr.includes('должен быть не менее') ||
       errorMsgStr.includes('Никнейм'))) {
    return errorMsgStr;
  }
  
  // Нормализуем тип ошибки (на случай если приходит с пробелами или в другом формате)
  const normalizedType = String(errorType).toLowerCase().trim();
  
  // Специальная обработка для ошибок длины никнейма (приоритетная проверка)
  if (fieldName === 'Никнейм') {
    if (normalizedType === 'string_too_long' || 
        errorMsgStr.includes('at most 15') || 
        errorMsgStr.includes('max_length') ||
        errorMsgStr.includes('should have at most')) {
      return 'Слишком длинный nickname';
    }
    if (normalizedType === 'string_too_short' || 
        errorMsgStr.includes('at least') || 
        errorMsgStr.includes('min_length') ||
        errorMsgStr.includes('should have at least')) {
      const match = errorMsgStr.match(/at least (\d+)|min_length[=:](\d+)/);
      const minLength = match ? (match[1] || match[2]) : '3';
      return `Никнейм должен быть не менее ${minLength} символов`;
    }
  }
  
  // Обработка различных типов ошибок
  switch (normalizedType) {
    case 'missing':
      return `${fieldName} обязателен`;
    
    case 'string_too_long':
      return fieldName === 'Никнейм' ? 'Слишком длинный nickname' : `${fieldName} слишком длинный`;
    
    case 'string_too_short':
      if (fieldName === 'Никнейм') {
        const match = errorMsgStr.match(/at least (\d+)|min_length[=:](\d+)/);
        const minLength = match ? (match[1] || match[2]) : '3';
        return `Никнейм должен быть не менее ${minLength} символов`;
      }
      return `${fieldName} слишком короткий`;
    
    case 'value_error':
      // Если сообщение содержит информацию о доступных ящиках, возвращаем его как есть
      if (errorMsgStr && (errorMsgStr.includes('Доступные ящики') || errorMsgStr.includes('mail.ru') || errorMsgStr.includes('yandex.ru') || errorMsgStr.includes('gmail.com'))) {
        return errorMsgStr;
      }
      if (errorMsgStr && (errorMsgStr.includes('email') || errorMsgStr.includes('EmailStr'))) {
        return `Неверный формат ${fieldName.toLowerCase()}`;
      }
      if (errorMsgStr && errorMsgStr.includes('max_length')) {
        if (fieldName === 'Никнейм') {
          return 'Слишком длинный nickname';
        }
        return `${fieldName} слишком длинный`;
      }
      if (errorMsgStr && errorMsgStr.includes('min_length')) {
        const match = errorMsgStr.match(/min_length=(\d+)/);
        const minLength = match ? match[1] : '8';
        return `${fieldName} должен быть не менее ${minLength} символов`;
      }
      // Если сообщение уже на русском и понятное, возвращаем его
      if (errorMsgStr && errorMsgStr.length > 0) {
        return errorMsgStr;
      }
      return `Неверное значение ${fieldName.toLowerCase()}`;
    
    case 'type_error':
      return `Неверный тип данных для ${fieldName.toLowerCase()}`;
    
    case 'string_type':
      return `${fieldName} должен быть строкой`;
    
    case 'email':
      return `Неверный формат ${fieldName.toLowerCase()}`;
    
    default:
      // Если сообщение уже на русском или содержит полезную информацию
      if (errorMsgStr && errorMsgStr.length > 0) {
        // Пытаемся извлечь полезную информацию из английского сообщения
        if (errorMsgStr.includes('required')) {
          return `${fieldName} обязателен`;
        }
        if (errorMsgStr.includes('not a valid')) {
          return `Неверный формат ${fieldName.toLowerCase()}`;
        }
        if (errorMsgStr.includes('length') || errorMsgStr.includes('max_length') || errorMsgStr.includes('min_length')) {
          // Если это ошибка max_length для nickname
          if (errorMsgStr.includes('max_length') && fieldName === 'Никнейм') {
            return 'Слишком длинный nickname';
          }
          // Если это ошибка min_length для nickname
          if (errorMsgStr.includes('min_length') && fieldName === 'Никнейм') {
            const match = errorMsgStr.match(/min_length=(\d+)/);
            const minLength = match ? match[1] : '3';
            return `Никнейм должен быть не менее ${minLength} символов`;
          }
          return `Неверная длина ${fieldName.toLowerCase()}`;
        }
        // Если сообщение понятное, возвращаем его
        return errorMsgStr;
      }
      return `Ошибка в поле ${fieldName.toLowerCase()}`;
  }
}

/**
 * Форматирует ошибку HTTP ответа
 * @param {Response} response - Объект Response от fetch
 * @param {Object} errorData - Данные ошибки из response.json()
 * @returns {string} - Отформатированное сообщение об ошибке
 */
export function formatHttpError(response, errorData) {
  // Для разных статусов возвращаем разные сообщения
  switch (response.status) {
    case 401:
      return 'Пользователя под таким аккаунтом не существует';
    
    case 403:
      return errorData.detail || 'Доступ запрещен';
    
    case 404:
      return errorData.detail || 'Ресурс не найден';
    
    case 422:
      // Ошибка валидации - используем форматирование
      return formatApiError(errorData);
    
    case 500:
      return 'Внутренняя ошибка сервера. Попробуйте позже';
    
    default:
      // Для других ошибок используем общее форматирование
      return formatApiError(errorData) || `Ошибка ${response.status}`;
  }
}

