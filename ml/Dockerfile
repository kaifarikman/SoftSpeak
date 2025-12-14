FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface
ENV HF_HOME=/app/.cache/huggingface
ENV HF_HUB_DISABLE_PROGRESS_BARS=1
ENV HF_HUB_DOWNLOAD_TIMEOUT=1800
ENV TRANSFORMERS_OFFLINE=0

RUN mkdir -p /app/.cache/huggingface

RUN pip install --no-cache-dir --upgrade pip && \
    (pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu || \
     pip install --no-cache-dir torch torchvision)

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
