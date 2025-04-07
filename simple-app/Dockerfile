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

# Открываем порт
EXPOSE 5000

# Запускаем приложение через Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"] 