FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Устанавливаем переменные окружения для оптимизации
ENV PYTHONUNBUFFERED=1
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface
ENV HF_HOME=/app/.cache/huggingface
ENV HF_HUB_DISABLE_PROGRESS_BARS=1
ENV HF_HUB_DOWNLOAD_TIMEOUT=1800
ENV TRANSFORMERS_OFFLINE=0

# Создаем директорию для кэша
RUN mkdir -p /app/.cache/huggingface

# Сначала устанавливаем torch и torchvision через специальный индекс
# Если не получится (например, на ARM64), fallback на обычный pip
RUN pip install --no-cache-dir --upgrade pip && \
    (pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu || \
     pip install --no-cache-dir torch torchvision)

# Копирование requirements и установка остальных зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Открываем порт
EXPOSE 8001

# Запуск приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]