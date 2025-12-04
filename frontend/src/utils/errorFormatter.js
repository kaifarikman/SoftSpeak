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
  // Обработка различных типов ошибок
  switch (errorType) {
    case 'missing':
      return `${fieldName} обязателен`;
    
    case 'value_error':
      if (errorMsg.includes('email') || errorMsg.includes('EmailStr')) {
        return `Неверный формат ${fieldName.toLowerCase()}`;
      }
      if (errorMsg.includes('min_length')) {
        const match = errorMsg.match(/min_length=(\d+)/);
        const minLength = match ? match[1] : '8';
        return `${fieldName} должен быть не менее ${minLength} символов`;
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
      if (errorMsg && typeof errorMsg === 'string') {
        // Пытаемся извлечь полезную информацию из английского сообщения
        if (errorMsg.includes('required')) {
          return `${fieldName} обязателен`;
        }
        if (errorMsg.includes('not a valid')) {
          return `Неверный формат ${fieldName.toLowerCase()}`;
        }
        if (errorMsg.includes('length')) {
          return `Неверная длина ${fieldName.toLowerCase()}`;
        }
        // Если сообщение понятное, возвращаем его
        return errorMsg;
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

