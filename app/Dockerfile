FROM python:3.9-slim

WORKDIR /app

# Устанавливаем необходимые системные зависимости для сборки psutil
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Настраиваем переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Устанавливаем здоровые таймауты для Gunicorn
ENV GUNICORN_TIMEOUT=120
ENV GUNICORN_WORKERS=2
ENV GUNICORN_THREADS=2

# Добавляем директиву HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:5000/healthz || exit 1

# Открываем порт
EXPOSE 5000

# Запускаем приложение через Gunicorn с обработкой сигналов и таймаутом
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "120", "--workers", "2", "--threads", "2", "--worker-class", "gthread", "--worker-tmp-dir", "/dev/shm", "--log-level", "info", "app:app"] 