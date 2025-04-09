#!/bin/bash

# Script to run the memory-increaser application for testing

# Default memory increment value
MEMORY_INCREMENT=10

# Display usage information
usage() {
  echo "Usage: $0 [OPTIONS]"
  echo "Run the memory increaser application with specified memory increment rate."
  echo ""
  echo "OPTIONS:"
  echo "  -m, --memory VALUE    Set memory increment in MB per second (default: $MEMORY_INCREMENT)"
  echo "  -h, --help            Display this help message"
  echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--memory)
      MEMORY_INCREMENT="$2"
      shift 2
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

# Check if the application dependencies are installed
if ! command -v pip &> /dev/null; then
  echo "Error: pip is not installed. Please install Python and pip first."
  exit 1
fi

# Check if requirements are installed
if ! pip list | grep -q "flask"; then
  echo "Installing dependencies..."
  pip install -r requirements.txt
  if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies."
    exit 1
  fi
fi

echo "Starting memory increaser with increment rate: $MEMORY_INCREMENT MB/s"
echo "Press Ctrl+C to stop the application"
echo ""

# Run the application with the specified memory increment
MEMORY_INCREMENT_MB=$MEMORY_INCREMENT python app.py 