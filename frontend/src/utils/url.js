import { API_URL, STATIC_ORIGIN } from '../config';

/**
 * Строит абсолютный URL для статических файлов (аватары и т.п.).
 * Поддерживает как Docker (относительные пути через Nginx), так и локальную разработку
 * с абсолютным API_URL.
 */
export function resolveStaticUrl(path) {
  if (!path) {
    return '';
  }

  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }

  let normalizedPath = path;
  if (!normalizedPath.startsWith('/')) {
    normalizedPath = `/${normalizedPath}`;
  }

  if (normalizedPath.startsWith('/static') || normalizedPath.startsWith('/uploads')) {
    if (STATIC_ORIGIN) {
      return `${STATIC_ORIGIN}${normalizedPath}`;
    }
    if (API_URL && API_URL.startsWith('http')) {
      try {
        const apiUrl = new URL(API_URL);
        return `${apiUrl.origin}${normalizedPath}`;
      } catch (error) {
        console.warn('resolveStaticUrl: не удалось распарсить API_URL', error);
      }
    }
    return normalizedPath;
  }

  return normalizedPath;
}

