# Resource Usage Controller

Простое веб-приложение для управления потреблением CPU и RAM внутри контейнера.

## Функциональность

- Веб-интерфейс для настройки уровня нагрузки CPU (0-100%)
- Настройка объема используемой оперативной памяти (0-1000 МБ)
- Мониторинг текущего потребления ресурсов в реальном времени

## Запуск приложения

### Локально

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Запустите приложение:
```bash
python app.py
```

3. Откройте в браузере http://localhost:5000

### В Docker-контейнере

1. Соберите Docker-образ:
```bash
docker build -t resource-controller .
```

2. Запустите контейнер:
```bash
docker run -p 5000:5000 resource-controller
```

3. Откройте в браузере http://localhost:5000

## Использование в Kubernetes

Пример манифеста для деплоя в Kubernetes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: resource-controller
spec:
  replicas: 1
  selector:
    matchLabels:
      app: resource-controller
  template:
    metadata:
      labels:
        app: resource-controller
    spec:
      containers:
      - name: resource-controller
        image: resource-controller:latest
        ports:
        - containerPort: 5000
        resources:
          limits:
            cpu: "1"
            memory: "1Gi"
          requests:
            cpu: "100m"
            memory: "128Mi"
``` 