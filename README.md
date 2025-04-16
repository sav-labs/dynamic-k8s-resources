# Dynamic Kubernetes Resource Manager (AIM)

A comprehensive solution for automated, intelligent management of Kubernetes pod resources. This project consists of two main components:

## 1. Controller

A Python-based Kubernetes controller that monitors and dynamically adjusts pod resources using the InPlacePodVerticalScaling feature. The controller integrates with metrics-server and Kube State Metrics to:

- Monitor CPU and memory usage of pods matching a specified label selector
- Dynamically adjust memory requests and limits based on actual usage patterns
- Update resource allocations without pod restarts using InPlacePodVerticalScaling
- Implement smart scaling policies with customizable thresholds
- Prevent resource oscillation through cooldown periods

**[View Controller Documentation](controller/README.md)**

## 2. Test Application

A simple web application for testing the dynamic resource controller by precisely increasing memory consumption at a configurable rate. Features include:

- Controlled memory consumption at a steady rate specified by environment variables
- Real-time memory usage monitoring with chart visualization
- Responsive web UI
- Kubernetes-ready with health checks
- Helm chart for easy deployment

**[View Test App Documentation](app/README.md)**

## Getting Started

1. Deploy the controller to your Kubernetes cluster:
   ```bash
   cd controller
   ./build_and_push.sh
   kubectl apply -f k8s.yaml
   ```

2. Deploy the test application with Helm:
   ```bash
   cd app
   ./build_and_push.sh
   helm install memory-test ./helm/resource-changer-app
   ```

3. Add the `dynamic-resources: "true"` label to pods you want to manage dynamically.

## Requirements

- Kubernetes cluster with metrics-server installed
- Kube State Metrics deployed in your cluster
- Kubernetes feature gate InPlacePodVerticalScaling=true enabled

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 