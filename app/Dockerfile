FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for psutil
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MEMORY_INCREMENT_MB=10

# Health check
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/healthz || exit 1

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"] 