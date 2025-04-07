#!/bin/bash

# Стоп при ошибке
set -e

# Устанавливаем переменные
IMAGE_NAME="sav116/resource-controller"
IMAGE_TAG=$(date +"%Y%m%d-%H%M%S")
IMAGE_TAG_GB="gb-$(date +"%Y%m%d-%H%M%S")"

# Выводим информацию о процессе
echo "Building Docker image: ${IMAGE_NAME}:${IMAGE_TAG_GB}"

# Собираем Docker образ
docker build -t ${IMAGE_NAME}:${IMAGE_TAG_GB} .
if [ $? -ne 0 ]; then
    echo "Error: Docker build failed!"
    exit 1
fi

# Добавляем тег latest
docker tag ${IMAGE_NAME}:${IMAGE_TAG_GB} ${IMAGE_NAME}:latest
echo "Docker image built successfully!"

# Отправляем образ в DockerHub
echo "Pushing image to DockerHub..."

# Проверяем, авторизован ли пользователь в DockerHub
DOCKER_LOGIN_STATUS=$(docker info 2>/dev/null | grep "Username" || echo "")
if [ -z "$DOCKER_LOGIN_STATUS" ]; then
    echo "You are not logged in to DockerHub. Please login first:"
    docker login
    
    # Проверяем успешность входа
    if [ $? -ne 0 ]; then
        echo "Error: Failed to login to DockerHub!"
        exit 1
    fi
fi

# Отправляем образы
# docker push ${IMAGE_NAME}:${IMAGE_TAG_GB}
# docker push ${IMAGE_NAME}:latest

# echo "Success! Images pushed to DockerHub:"
# echo "${IMAGE_NAME}:${IMAGE_TAG_GB}"
# echo "${IMAGE_NAME}:latest" 