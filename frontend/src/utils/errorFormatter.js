

export function formatApiError(errorData) {

  if (typeof errorData.detail === 'string') {
    return errorData.detail;
  }


  if (Array.isArray(errorData.detail)) {
    const errors = errorData.detail.map(error => {
      const field = error.loc && error.loc.length > 0 
        ? error.loc[error.loc.length - 1] 
        : 'поле';
      

      const fieldName = getFieldName(field);
      

      const message = getErrorMessage(error.type, error.msg, fieldName);
      
      return message;
    });


    return errors.join('. ');
  }


  if (errorData.detail && typeof errorData.detail === 'object') {
    return JSON.stringify(errorData.detail);
  }


  return 'Произошла ошибка при обработке запроса';
}



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



function getErrorMessage(errorType, errorMsg, fieldName) {

  const errorMsgStr = errorMsg && typeof errorMsg === 'string' ? errorMsg : String(errorMsg || '');
  

  if (errorMsgStr && 
      (errorMsgStr.includes('Слишком длинный') || 
       errorMsgStr.includes('должен быть не менее') ||
       errorMsgStr.includes('Никнейм'))) {
    return errorMsgStr;
  }
  

  const normalizedType = String(errorType).toLowerCase().trim();
  

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

      if (errorMsgStr && errorMsgStr.length > 0) {

        if (errorMsgStr.includes('required')) {
          return `${fieldName} обязателен`;
        }
        if (errorMsgStr.includes('not a valid')) {
          return `Неверный формат ${fieldName.toLowerCase()}`;
        }
        if (errorMsgStr.includes('length') || errorMsgStr.includes('max_length') || errorMsgStr.includes('min_length')) {

          if (errorMsgStr.includes('max_length') && fieldName === 'Никнейм') {
            return 'Слишком длинный nickname';
          }

          if (errorMsgStr.includes('min_length') && fieldName === 'Никнейм') {
            const match = errorMsgStr.match(/min_length=(\d+)/);
            const minLength = match ? match[1] : '3';
            return `Никнейм должен быть не менее ${minLength} символов`;
          }
          return `Неверная длина ${fieldName.toLowerCase()}`;
        }

        return errorMsgStr;
      }
      return `Ошибка в поле ${fieldName.toLowerCase()}`;
  }
}



export function formatHttpError(response, errorData) {

  switch (response.status) {
    case 401:
      return 'Пользователя под таким аккаунтом не существует';
    
    case 403:
      return errorData.detail || 'Доступ запрещен';
    
    case 404:
      return errorData.detail || 'Ресурс не найден';
    
    case 422:

      return formatApiError(errorData);
    
    case 500:
      return 'Внутренняя ошибка сервера. Попробуйте позже';
    
    default:

      return formatApiError(errorData) || `Ошибка ${response.status}`;
  }
}

