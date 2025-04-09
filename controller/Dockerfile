FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Команда запуска (может быть переопределена при запуске контейнера)
CMD ["python", "app.py"] 