export function resolveStaticUrl(path) {
  if (!path) {
    return '';
  }

  if (path.startsWith('http:
    return path;
  }

  let normalizedPath = path;
  if (!normalizedPath.startsWith('/')) {
    normalizedPath = `/${normalizedPath}`;
  }

  return normalizedPath;
}

