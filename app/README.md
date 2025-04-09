# Memory Increaser Application

A simple web application that precisely increases memory consumption by a configurable amount (in MB) per second. This application is designed for testing memory limits, autoscaling, and OOM behaviors in Kubernetes.

## Features

- Increases memory consumption at a steady rate specified by an environment variable
- Real-time memory usage monitoring with chart visualization
- Clean, responsive web UI
- Kubernetes-ready with health checks
- Helm chart for easy deployment

## Configuration

The application is configured using the following environment variable:

- `MEMORY_INCREMENT_MB`: Memory consumption rate in MB per second (default: 10)

## Local Development

### Prerequisites

- Python 3.9+
- Docker (optional)

### Running Locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the application:

```bash
python app.py
```

3. Access the web interface at http://localhost:5000

### Building and Running with Docker

1. Build the Docker image:

```bash
docker build -t memory-increaser .
```

2. Run the container:

```bash
docker run -p 5000:5000 -e MEMORY_INCREMENT_MB=20 memory-increaser
```

3. Access the web interface at http://localhost:5000

## Kubernetes Deployment with Helm

### Prerequisites

- Kubernetes cluster
- Helm 3

### Deployment

1. Update the values in `helm/resource-changer-app/values.yaml` as needed

2. Install the chart:

```bash
helm install memory-increaser ./helm/resource-changer-app
```

3. To update the memory increment rate:

```bash
helm upgrade memory-increaser ./helm/resource-changer-app --set env.MEMORY_INCREMENT_MB=30
```

### Checking Memory Usage

You can use the following command to see the memory usage of the pod:

```bash
kubectl top pod -l app.kubernetes.io/name=resource-changer-app
```

## How It Works

The application creates a Python thread that allocates a fixed amount of memory (specified by `MEMORY_INCREMENT_MB`) every second and stores it in a global list. This causes a predictable linear increase in memory consumption that can be observed in Kubernetes. 