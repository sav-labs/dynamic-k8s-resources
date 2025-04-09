#!/bin/bash

# Стоп при ошибке
set -e

# Цветные сообщения для улучшения читаемости
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Устанавливаем переменные
IMAGE_NAME="sav116/resource-changer-app"
IMAGE_TAG=$(date +"%Y%m%d-%H%M%S")
IMAGE_TAG_GB="gb-$(date +"%Y%m%d-%H%M%S")"

# Функция для вывода статуса
progress() {
    echo -e "${YELLOW}[BUILD] $1${NC}"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    error "Docker не установлен. Пожалуйста, установите Docker."
fi

# Выводим информацию о процессе
progress "Building Docker image: ${IMAGE_NAME}:${IMAGE_TAG_GB}"

# Проверка наличия Dockerfile
if [ ! -f "Dockerfile" ]; then
    error "Dockerfile не найден в текущей директории!"
fi

# Собираем Docker образ
docker build -t ${IMAGE_NAME}:${IMAGE_TAG_GB} .
if [ $? -ne 0 ]; then
    error "Docker build failed!"
fi

# Добавляем тег latest
docker tag ${IMAGE_NAME}:${IMAGE_TAG_GB} ${IMAGE_NAME}:latest
success "Docker image built successfully!"

# Базовая проверка образа перед отправкой
progress "Performing basic health check on the image..."
docker run --rm -d --name health_check -p 5000:5000 ${IMAGE_NAME}:${IMAGE_TAG_GB}
sleep 10

# Проверка работоспособности приложения
curl -s localhost:5000/healthz > /dev/null
if [ $? -ne 0 ]; then
    docker stop health_check
    error "Health check failed! Not pushing to repository."
fi

docker stop health_check
success "Health check passed!"

# Отправляем образ в DockerHub
progress "Pushing image to DockerHub..."

# Проверяем, авторизован ли пользователь в DockerHub
DOCKER_LOGIN_STATUS=$(docker info 2>/dev/null | grep "Username" || echo "")
if [ -z "$DOCKER_LOGIN_STATUS" ]; then
    progress "You are not logged in to DockerHub. Please login first:"
    docker login
    
    # Проверяем успешность входа
    if [ $? -ne 0 ]; then
        error "Failed to login to DockerHub!"
    fi
fi

# Отправляем образы
docker push ${IMAGE_NAME}:${IMAGE_TAG_GB}
docker push ${IMAGE_NAME}:latest

success "Images pushed to DockerHub:"
echo "  ${IMAGE_NAME}:${IMAGE_TAG_GB}"
echo "  ${IMAGE_NAME}:latest"

# Инструкции по обновлению деплоя
echo
progress "To update deployment, run:"
echo "  helm upgrade resource-changer-app ./helm/resource-changer-app/"
echo 