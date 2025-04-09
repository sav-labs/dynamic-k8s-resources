#!/bin/bash

# Script to build and push the memory-increaser Docker image

# Default values
IMAGE_NAME="memory-increaser"
IMAGE_TAG="latest"
DOCKER_REGISTRY_PREFIX=""
PUSH_IMAGE=false
BUILD_IMAGE=true

# Display usage information
usage() {
  echo "Usage: $0 [OPTIONS]"
  echo "Build and push a Docker image for the memory increaser application."
  echo ""
  echo "OPTIONS:"
  echo "  -n, --name NAME       Set the image name (default: $IMAGE_NAME)"
  echo "  -t, --tag TAG         Set the image tag (default: $IMAGE_TAG)"
  echo "  -r, --registry REG    Set Docker registry prefix (default: none)"
  echo "  -p, --push            Push the image after building"
  echo "  --no-build            Skip building the image"
  echo "  -h, --help            Display this help message"
  echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--name)
      IMAGE_NAME="$2"
      shift 2
      ;;
    -t|--tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    -r|--registry)
      DOCKER_REGISTRY_PREFIX="$2/"
      shift 2
      ;;
    -p|--push)
      PUSH_IMAGE=true
      shift
      ;;
    --no-build)
      BUILD_IMAGE=false
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

# Full image name with registry and tag
FULL_IMAGE_NAME="${DOCKER_REGISTRY_PREFIX}${IMAGE_NAME}:${IMAGE_TAG}"

# Build the Docker image
if [ "$BUILD_IMAGE" = true ]; then
  echo "Building Docker image: $FULL_IMAGE_NAME"
  docker build -t "$FULL_IMAGE_NAME" .
  
  if [ $? -ne 0 ]; then
    echo "Error: Docker build failed"
    exit 1
  fi
  
  echo "Docker image built successfully."
else
  echo "Skipping image build."
fi

# Push the Docker image
if [ "$PUSH_IMAGE" = true ]; then
  echo "Pushing Docker image: $FULL_IMAGE_NAME"
  docker push "$FULL_IMAGE_NAME"
  
  if [ $? -ne 0 ]; then
    echo "Error: Docker push failed"
    exit 1
  fi
  
  echo "Docker image pushed successfully."
fi

echo "Done!" 