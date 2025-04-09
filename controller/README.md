# Kubernetes Dynamic Resource Manager

This Python controller integrates with Kubernetes metrics-server and Kube State Metrics to monitor and dynamically adjust pod resources using the InPlacePodVerticalScaling feature.

## Features

- Monitors CPU and memory usage of pods matching a specified label selector
- Dynamically adjusts memory requests and limits based on actual usage patterns
- Uses InPlacePodVerticalScaling to update resource allocations without pod restarts
- Implements smart scaling policies with customizable thresholds
- Includes cooldown periods to prevent resource oscillation
- Configurable through environment variables

## Requirements

- Kubernetes cluster with metrics-server installed and running
- Kube State Metrics deployed in your cluster
- Kubernetes feature gate InPlacePodVerticalScaling=true enabled
- Pods with the label defined in the LABEL_SELECTOR environment variable

## Local Development

1. Install required Python dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Ensure your `kubectl` is configured to connect to your Kubernetes cluster

3. Run the resource manager:
   ```
   python app.py
   ```

## Environment Variables

The controller supports the following environment variables:

| Variable | Description | Default Value |
|------------|----------|------------------------|
| `METRICS_SERVER_URL` | URL to access the metrics-server | `https://metrics-server.kube-system.svc.cluster.local` |
| `VERIFY_CERT` | Whether to verify SSL certificates when making requests | `true` |
| `METRICS_FETCH_INTERVAL` | Interval between metrics checks (in seconds) | `30` |
| `KUBE_STATE_METRICS_URL` | URL to access the Kube State Metrics API | Not set |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `LABEL_SELECTOR` | Label selector to filter pods for monitoring | Not set - monitors all pods |
| `SCALE_UP_THRESHOLD` | Memory usage ratio threshold to trigger scaling up | `0.8` (80%) |
| `SCALE_UP_USAGE_MULTIPLIER` | Multiplier applied to current usage when scaling up | `1.4` (140%) |
| `SCALE_DOWN_USAGE_MULTIPLIER` | Multiplier applied to current usage when scaling down | `2.5` (250%) |
| `COOLDOWN_PERIOD_SECONDS` | Seconds to wait after scaling before allowing scale down | `600` (10 minutes) |
| `MIN_REQUEST_MEMORY` | Minimum memory request in MiB | `100` |

## Deployment to Kubernetes

1. Build the Docker image:
   ```
   ./build_and_push.sh
   ```
   
   Or manually:
   ```
   docker build -t your-registry/dynamic-resource-manager:latest .
   docker push your-registry/dynamic-resource-manager:latest
   ```

2. Update the image name in `k8s.yaml` to your registry path

3. Configure environment variables in the ConfigMap inside `k8s.yaml`

4. Apply the Kubernetes manifests:
   ```
   kubectl apply -f k8s.yaml
   ```

## How It Works

### Resource Scaling Logic

The resource manager implements the following logic:

1. **Scale Up Trigger**:
   - When a pod's memory usage reaches ≥ SCALE_UP_THRESHOLD (default 80%) of its allocated memory
   - Immediately increases resources to prevent OOM kills
   - New allocation = max(usage * SCALE_UP_USAGE_MULTIPLIER, request * SCALE_UP_MIN_GROWTH)
   - Defaults provide at least 120% of the previous allocation or 140% of current usage

2. **Scale Down Trigger**:
   - When a pod's memory usage is consistently ≤ SCALE_DOWN_THRESHOLD (default 30%)
   - Only scales down if the cooldown period has elapsed since the last resize
   - New allocation = max(usage * SCALE_DOWN_USAGE_MULTIPLIER, MIN_REQUEST_MEMORY)
   - Only scales down if the reduction is at least SCALE_DOWN_MIN_DIFF (default 20%)

3. **Cooldown Mechanism**:
   - After each resource change, records a timestamp in the pod's annotations
   - Prevents frequent oscillations by enforcing a minimum time between scaling operations
   - Only applies to scale-down operations (scale-up is immediate for safety)

### Implementation Details

The controller consists of several key components:

- **KubernetesClient**: Base class for authentication and API communication
- **KubeStateMetricsClient**: Fetches and parses container resource requests/limits
- **MetricsServerClient**: Retrieves current CPU and memory usage
- **KubernetesApiClient**: Updates pod resources and annotations
- **ResourceManager**: Implements the scaling logic and decision-making

The controller uses the Kubernetes API with the InPlacePodVerticalScaling feature to modify pod resources without restarts, making it suitable for production environments.

## Extending the Controller

You can modify the code to:
- Adjust CPU resources in addition to memory
- Implement more sophisticated scaling algorithms
- Add alerts when pods approach their resource limits
- Store historical metrics for trend analysis
- Integrate with monitoring systems for visualization 