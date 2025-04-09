#!/bin/bash

# Скрипт для сборки и отправки Docker-образа в публичный реестр

# Настройка цветов для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Установка переменных
IMAGE_NAME="sav116/resource-changer-controller"
TAG="latest"

# Вывод разделителя
echo -e "${YELLOW}=======================================================${NC}"
echo -e "${GREEN}Building and pushing Docker image for Resource Controller${NC}"
echo -e "${YELLOW}=======================================================${NC}"

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker not found! Please install Docker first.${NC}"
    exit 1
fi

# Сборка Docker-образа
echo -e "${GREEN}Building Docker image: ${IMAGE_NAME}:${TAG}${NC}"
docker build -t ${IMAGE_NAME}:${TAG} .

# Проверка успешности сборки
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to build Docker image!${NC}"
    exit 1
fi

echo -e "${GREEN}Docker image built successfully!${NC}"

# Отправка Docker-образа в реестр
echo -e "${GREEN}Pushing Docker image to registry: ${IMAGE_NAME}:${TAG}${NC}"
docker push ${IMAGE_NAME}:${TAG}

# Проверка успешности отправки
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to push Docker image to registry!${NC}"
    exit 1
fi

echo -e "${GREEN}Docker image pushed successfully!${NC}"
echo -e "${GREEN}Image: ${IMAGE_NAME}:${TAG}${NC}"

# Вывод инструкций по использованию
echo -e "${YELLOW}=======================================================${NC}"
echo -e "${GREEN}To use this image in Kubernetes:${NC}"
echo -e "${YELLOW}1. Apply the Kubernetes deployment:${NC}"
echo -e "   kubectl apply -f k8s.yaml"
echo -e "${YELLOW}=======================================================${NC}"

exit 0 