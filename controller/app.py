#!/usr/bin/env python3
import os
import re
import requests
import logging
import time
import urllib3
import json
from datetime import datetime, timedelta

# Disable InsecureRequestWarning when verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class KubernetesClient:
    """Base class to handle Kubernetes API communication"""
    
    def __init__(self):
        self.verify_cert = os.environ.get("VERIFY_CERT", "true").lower() in ("true", "1", "t")
        
    def get_auth_headers(self):
        """
        Returns authentication headers with Bearer Token.
        First tries to get token from K8S_BEARER_TOKEN environment variable.
        If not found, reads ServiceAccount token from /var/run/secrets/kubernetes.io/serviceaccount/token.
        """
        token = os.environ.get('K8S_BEARER_TOKEN')
        if not token:
            token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
            if os.path.exists(token_path):
                with open(token_path, "r") as token_file:
                    token = token_file.read().strip()
        if token:
            return {"Authorization": f"Bearer {token}"}
        else:
            logging.error("Authentication token not found (K8S_BEARER_TOKEN or ServiceAccount).")
            return {}


class KubeStateMetricsClient(KubernetesClient):
    """Client for fetching and parsing Kube State Metrics"""
    
    def __init__(self):
        super().__init__()
        self.kube_state_url = os.environ.get('KUBE_STATE_METRICS_URL')
        if not self.kube_state_url:
            logging.warning("Environment variable 'KUBE_STATE_METRICS_URL' not set; cannot get requests/limits.")
    
    def fetch_metrics(self):
        """
        Makes a request to Kube State Metrics and returns
        a dictionary with resource (requests/limits) for each container.
        """
        if not self.kube_state_url:
            return {}

        try:
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                logging.debug(f"Fetching data from Kube State Metrics")
                
            resp = requests.get(self.kube_state_url, verify=self.verify_cert)
            resp.raise_for_status()
        except requests.RequestException as e:
            logging.error(f"Error requesting Kube State Metrics: {e}")
            return {}

        data = self.parse_metrics(resp.text)
        
        if not data and logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug("No resource data obtained from Kube State Metrics")
            
        return data
    
    def parse_metrics(self, text):
        """
        Parses text metrics in Prometheus format from Kube State Metrics
        and returns a dictionary in the format:
        {
          (namespace, pod, container): {
             'requests_cpu_cores': float,
             'requests_mem_mib': float,
             'limits_cpu_cores': float,
             'limits_mem_mib': float
          },
          ...
        }
        """
        # Regular expressions matching real metrics format
        lim_cpu_pattern = re.compile(
            r'^kube_pod_container_resource_limits\{.*?namespace="([^"]+)",pod="([^"]+)".*?container="([^"]+)".*?resource="cpu".*?\}\s+([\d\.eE\+\-]+)'
        )
        
        lim_mem_pattern = re.compile(
            r'^kube_pod_container_resource_limits\{.*?namespace="([^"]+)",pod="([^"]+)".*?container="([^"]+)".*?resource="memory".*?\}\s+([\d\.eE\+\-]+)'
        )
        
        req_cpu_pattern = re.compile(
            r'^kube_pod_container_resource_requests\{.*?namespace="([^"]+)",pod="([^"]+)".*?container="([^"]+)".*?resource="cpu".*?\}\s+([\d\.eE\+\-]+)'
        )
        
        req_mem_pattern = re.compile(
            r'^kube_pod_container_resource_requests\{.*?namespace="([^"]+)",pod="([^"]+)".*?container="([^"]+)".*?resource="memory".*?\}\s+([\d\.eE\+\-]+)'
        )

        data = {}

        def ensure_key(ns, pod, cont):
            if (ns, pod, cont) not in data:
                data[(ns, pod, cont)] = {
                    'requests_cpu_cores': 0.0,
                    'requests_mem_mib': 0.0,
                    'limits_cpu_cores': 0.0,
                    'limits_mem_mib': 0.0
                }

        for line in text.splitlines():
            line = line.strip()
            if line.startswith('#') or not line:  # Skip comments and empty lines
                continue

            # Find Request CPU
            match = req_cpu_pattern.match(line)
            if match:
                namespace, pod, container, val = match.groups()
                val = float(val)  # cores
                ensure_key(namespace, pod, container)
                data[(namespace, pod, container)]['requests_cpu_cores'] = val
                continue

            # Find Request Memory
            match = req_mem_pattern.match(line)
            if match:
                namespace, pod, container, val = match.groups()
                val = float(val) / (1024 * 1024)  # bytes -> MiB
                ensure_key(namespace, pod, container)
                data[(namespace, pod, container)]['requests_mem_mib'] = val
                continue

            # Find Limit CPU
            match = lim_cpu_pattern.match(line)
            if match:
                namespace, pod, container, val = match.groups()
                val = float(val)  # cores
                ensure_key(namespace, pod, container)
                data[(namespace, pod, container)]['limits_cpu_cores'] = val
                continue

            # Find Limit Memory
            match = lim_mem_pattern.match(line)
            if match:
                namespace, pod, container, val = match.groups()
                val = float(val) / (1024 * 1024)  # bytes -> MiB
                ensure_key(namespace, pod, container)
                data[(namespace, pod, container)]['limits_mem_mib'] = val
                continue

        return data


class MetricsServerClient(KubernetesClient):
    """Client for fetching data from Metrics Server"""
    
    def __init__(self):
        super().__init__()
        self.metrics_server_url = os.environ.get('METRICS_SERVER_URL')
        if not self.metrics_server_url:
            logging.error("Environment variable 'METRICS_SERVER_URL' not set.")
        
        self.label_selector = os.environ.get('LABEL_SELECTOR')
    
    def fetch_metrics(self):
        """
        Makes a request to Metrics Server and returns memory/CPU usage metrics.
        """
        if not self.metrics_server_url:
            return None

        url = f"{self.metrics_server_url}/apis/metrics.k8s.io/v1beta1/pods"
        
        params = {}
        if self.label_selector:
            params["labelSelector"] = self.label_selector
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                logging.debug(f"Using labelSelector: {self.label_selector}")
        
        headers = self.get_auth_headers()

        try:
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                logging.debug(f"Fetching metrics from Metrics Server")
                
            response = requests.get(url, params=params, headers=headers, verify=self.verify_cert)
            response.raise_for_status()
        except requests.RequestException as e:
            logging.error(f"Error fetching metrics from Metrics Server: {e}")
            return None

        return response.json()
    
    def parse_pod_metrics(self, pod_metrics, state_data):
        """
        Parses pod metrics and returns dictionary with usage data
        {
          (namespace, pod_name, container_name): {
             'cpu_usage': float,  # in cores
             'memory_usage': float,  # in MiB
             'requests_cpu_cores': float,
             'requests_mem_mib': float,
             'limits_cpu_cores': float,
             'limits_mem_mib': float
          },
          ...
        }
        """
        result = {}
        
        if not pod_metrics:
            return result
            
        for pod in pod_metrics:
            metadata = pod.get("metadata", {})
            namespace = metadata.get("namespace", "unknown")
            pod_name = metadata.get("name", "unknown")
            
            for container in pod.get("containers", []):
                container_name = container.get("name", "unknown")
                usage = container.get("usage", {})

                # Convert CPU usage to cores
                cpu_usage = usage.get("cpu", "0")
                cpu_value = 0.0
                if cpu_usage.endswith("n"):
                    cpu_value = int(cpu_usage[:-1]) / 1e9
                elif cpu_usage.endswith("u"):
                    cpu_value = int(cpu_usage[:-1]) / 1e6
                elif cpu_usage.endswith("m"):
                    cpu_value = float(cpu_usage[:-1]) / 1000.0
                else:
                    # If simply "1", "2", "1.5" etc.
                    try:
                        cpu_value = float(cpu_usage)
                    except ValueError:
                        cpu_value = 0.0

                # Convert Memory usage to MiB
                memory_usage = usage.get("memory", "0")
                memory_value = 0.0
                if memory_usage.endswith("Ki"):
                    memory_value = float(memory_usage[:-2]) / 1024.0
                elif memory_usage.endswith("Mi"):
                    memory_value = float(memory_usage[:-2])
                elif memory_usage.endswith("Gi"):
                    memory_value = float(memory_usage[:-2]) * 1024.0
                elif memory_usage.endswith("K") or memory_usage.endswith("k"):
                    memory_value = float(memory_usage[:-1]) / 1024.0
                elif memory_usage.endswith("M"):
                    memory_value = float(memory_usage[:-1])
                elif memory_usage.endswith("G"):
                    memory_value = float(memory_usage[:-1]) * 1024.0
                else:
                    # Bytes (e.g. "123456")?
                    try:
                        memory_value = float(memory_usage) / (1024.0 * 1024.0)
                    except ValueError:
                        memory_value = 0.0

                # Get requests/limits from Kube State Metrics
                rsrc_key = (namespace, pod_name, container_name)
                rsrc = state_data.get(rsrc_key, {})
                
                # If not found, try different pod name matching patterns
                if not rsrc:
                    # Typical pattern for pod name: deployment-name-random-id-random-id
                    # Try to find a match by partial name
                    matched = False
                    
                    # 1. Check for exact match
                    if rsrc_key in state_data:
                        rsrc = state_data[rsrc_key]
                        matched = True
                        if logging.getLogger().isEnabledFor(logging.DEBUG):
                            logging.debug(f"Found exact match for {rsrc_key}")
                    
                    # 2. Try to find by partial name (usually deployment-name-*)
                    if not matched and '-' in pod_name:
                        # Try to find by first N parts of name (removing replicaset and pod suffixes)
                        parts = pod_name.split('-')
                        for i in range(len(parts) - 1, 0, -1):
                            # Create base name starting with 1, 2, ... parts
                            base_name = '-'.join(parts[:i])
                            if logging.getLogger().isEnabledFor(logging.DEBUG):
                                logging.debug(f"Trying to find {namespace}/{base_name}-* for {pod_name}")
                            
                            # Find any key where namespace matches and pod name starts with base_name
                            for key, value in state_data.items():
                                if key[0] == namespace and key[2] == container_name and key[1].startswith(base_name):
                                    rsrc = value
                                    matched = True
                                    if logging.getLogger().isEnabledFor(logging.DEBUG):
                                        logging.debug(f"Found match {key} for {namespace}/{pod_name}/{container_name}")
                                    break
                            
                            if matched:
                                break
                
                req_cpu = rsrc.get("requests_cpu_cores", 0.0)
                req_mem = rsrc.get("requests_mem_mib", 0.0)
                lim_cpu = rsrc.get("limits_cpu_cores", 0.0)
                lim_mem = rsrc.get("limits_mem_mib", 0.0)
                
                result[rsrc_key] = {
                    'cpu_usage': cpu_value,
                    'memory_usage': memory_value,
                    'requests_cpu_cores': req_cpu,
                    'requests_mem_mib': req_mem,
                    'limits_cpu_cores': lim_cpu,
                    'limits_mem_mib': lim_mem
                }
                
                if logging.getLogger().isEnabledFor(logging.DEBUG):
                    logging.debug(
                        f"Pod {namespace}/{pod_name}, Container {container_name} => "
                        f"Usage: CPU {cpu_value:.3f} cores / Mem {memory_value:.2f}Mi; "
                        f"Request: CPU {req_cpu:.3f} / Mem {req_mem:.2f}Mi; "
                        f"Limit: CPU {lim_cpu:.3f} / Mem {lim_mem:.2f}Mi"
                    )
                    
        return result


class KubernetesApiClient(KubernetesClient):
    """Client for Kubernetes API operations"""
    
    def __init__(self):
        super().__init__()
        self.api_server_url = os.environ.get('KUBERNETES_API_SERVER', 'https://kubernetes.default.svc')
        
    def patch_pod_resources(self, namespace, pod_name, container_name, memory_request, memory_limit=None):
        """
        Updates pod resources using the Kubernetes API with InPlacePodVerticalScaling
        """
        if memory_limit is None:
            memory_limit = memory_request
            
        # Format memory values to Kubernetes format (e.g., "100Mi")
        memory_request_str = f"{int(memory_request)}Mi"
        memory_limit_str = f"{int(memory_limit)}Mi"
        
        url = f"{self.api_server_url}/api/v1/namespaces/{namespace}/pods/{pod_name}"
        headers = self.get_auth_headers()
        headers["Content-Type"] = "application/strategic-merge-patch+json"
        
        # Prepare the patch payload
        patch_body = {
            "spec": {
                "containers": [
                    {
                        "name": container_name,
                        "resources": {
                            "requests": {
                                "memory": memory_request_str
                            },
                            "limits": {
                                "memory": memory_limit_str
                            }
                        }
                    }
                ]
            }
        }
        
        try:
            logging.info(f"Updating resources for pod {namespace}/{pod_name} container {container_name} to {memory_request_str}")
            response = requests.patch(
                url, 
                json=patch_body,
                headers=headers,
                verify=self.verify_cert
            )
            response.raise_for_status()
            
            # Update annotation with timestamp
            self.update_last_scale_annotation(namespace, pod_name)
            
            return True
        except requests.RequestException as e:
            logging.error(f"Failed to update pod resources: {e}")
            if hasattr(e, 'response') and e.response:
                logging.error(f"Response: {e.response.text}")
            return False
    
    def update_last_scale_annotation(self, namespace, pod_name):
        """
        Updates the pod with an annotation tracking the last scaling time
        """
        url = f"{self.api_server_url}/api/v1/namespaces/{namespace}/pods/{pod_name}"
        headers = self.get_auth_headers()
        headers["Content-Type"] = "application/strategic-merge-patch+json"
        
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        patch_body = {
            "metadata": {
                "annotations": {
                    "resource-manager/last-update": timestamp
                }
            }
        }
        
        try:
            response = requests.patch(
                url, 
                json=patch_body,
                headers=headers,
                verify=self.verify_cert
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logging.error(f"Failed to update pod annotation: {e}")
            return False
            
    def get_pod_annotations(self, namespace, pod_name):
        """
        Gets pod annotations
        """
        url = f"{self.api_server_url}/api/v1/namespaces/{namespace}/pods/{pod_name}"
        headers = self.get_auth_headers()
        
        try:
            response = requests.get(
                url,
                headers=headers,
                verify=self.verify_cert
            )
            response.raise_for_status()
            pod_data = response.json()
            return pod_data.get("metadata", {}).get("annotations", {})
        except requests.RequestException as e:
            logging.error(f"Failed to get pod annotations: {e}")
            return {}


class ResourceManager:
    """
    Manager to monitor and adjust pod resources based on actual usage
    """
    
    def __init__(self):
        # Initialize clients
        self.kube_state_client = KubeStateMetricsClient()
        self.metrics_client = MetricsServerClient()
        self.k8s_client = KubernetesApiClient()
        
        # Load configuration from environment variables with defaults
        self.scale_up_threshold = float(os.environ.get('SCALE_UP_THRESHOLD', '0.8'))
        self.scale_up_usage_multiplier = float(os.environ.get('SCALE_UP_USAGE_MULTIPLIER', '1.4'))
        self.scale_up_min_growth = float(os.environ.get('SCALE_UP_MIN_GROWTH', '1.2'))
        
        self.scale_down_threshold = float(os.environ.get('SCALE_DOWN_THRESHOLD', '0.3'))
        self.scale_down_usage_multiplier = float(os.environ.get('SCALE_DOWN_USAGE_MULTIPLIER', '2.5'))
        self.scale_down_min_diff = float(os.environ.get('SCALE_DOWN_MIN_DIFF', '0.2'))
        
        self.min_request_memory = float(os.environ.get('MIN_REQUEST_MEMORY', '100'))
        self.cooldown_period_seconds = int(os.environ.get('COOLDOWN_PERIOD_SECONDS', '600'))
        
        self.metrics_fetch_interval = int(os.environ.get('METRICS_FETCH_INTERVAL', '30'))
        
        # Log configuration
        self._log_configuration()
        
    def _log_configuration(self):
        """Logs the configuration settings"""
        if logging.getLogger().isEnabledFor(logging.INFO):
            logging.info("Resource Manager configuration:")
            logging.info(f"- Scale Up: threshold={self.scale_up_threshold}, multiplier={self.scale_up_usage_multiplier}, min_growth={self.scale_up_min_growth}")
            logging.info(f"- Scale Down: threshold={self.scale_down_threshold}, multiplier={self.scale_down_usage_multiplier}, min_diff={self.scale_down_min_diff}")
            logging.info(f"- Min memory request: {self.min_request_memory}Mi")
            logging.info(f"- Cooldown period: {self.cooldown_period_seconds} seconds")
            logging.info(f"- Metrics fetch interval: {self.metrics_fetch_interval} seconds")

    def run(self):
        """
        Main loop to monitor and manage resources
        """
        logging.info("Starting Resource Manager")
        
        while True:
            try:
                self._process_resources()
            except Exception as e:
                logging.error(f"Error in main loop: {e}", exc_info=True)
            
            time.sleep(self.metrics_fetch_interval)
    
    def _process_resources(self):
        """
        Process resources for all pods matching the label selector
        """
        # 1. Get resource data from Kube State Metrics
        state_data = self.kube_state_client.fetch_metrics()
        
        # 2. Get current usage metrics
        metrics_data = self.metrics_client.fetch_metrics()
        if not metrics_data:
            return
            
        # 3. Parse pod metrics
        pods_metrics = metrics_data.get("items", [])
        if not pods_metrics:
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                logging.debug("No pod metrics found")
            return
            
        # 4. Parse and process pod metrics
        parsed_metrics = self.metrics_client.parse_pod_metrics(pods_metrics, state_data)
        
        # 5. For each pod/container, determine if scaling is needed
        for (namespace, pod_name, container_name), metrics in parsed_metrics.items():
            self._evaluate_and_scale(namespace, pod_name, container_name, metrics)
    
    def _evaluate_and_scale(self, namespace, pod_name, container_name, metrics):
        """
        Evaluates if a container needs scaling and performs the scaling if needed
        """
        memory_usage = metrics['memory_usage']
        memory_request = metrics['requests_mem_mib']
        
        # Skip if there's no memory request set (can't determine ratios)
        if memory_request <= 0:
            return
            
        # Calculate usage ratio
        usage_ratio = memory_usage / memory_request
        
        # Check if we need to scale up
        if usage_ratio >= self.scale_up_threshold:
            self._scale_up(namespace, pod_name, container_name, memory_usage, memory_request)
        
        # Check if we need to scale down
        elif usage_ratio <= self.scale_down_threshold:
            self._scale_down(namespace, pod_name, container_name, memory_usage, memory_request)
    
    def _scale_up(self, namespace, pod_name, container_name, memory_usage, current_request):
        """
        Scales up container resources to prevent OOM
        """
        # Calculate new memory request based on current usage
        new_request_by_usage = memory_usage * self.scale_up_usage_multiplier
        new_request_by_min_growth = current_request * self.scale_up_min_growth
        
        # Take the maximum to ensure we have enough headroom
        new_memory_request = max(new_request_by_usage, new_request_by_min_growth)
        
        # Round to nearest integer for cleaner values
        new_memory_request = int(round(new_memory_request))
        
        logging.info(
            f"Pod {namespace}/{pod_name} container {container_name} memory usage ratio: {memory_usage/current_request:.2f} "
            f"- scaling UP from {current_request:.0f}Mi to {new_memory_request}Mi"
        )
        
        # Update the resources
        self.k8s_client.patch_pod_resources(
            namespace=namespace,
            pod_name=pod_name,
            container_name=container_name,
            memory_request=new_memory_request
        )
    
    def _scale_down(self, namespace, pod_name, container_name, memory_usage, current_request):
        """
        Scales down container resources if usage has been low for sufficient time
        """
        # Get pod annotations to check cooldown period
        annotations = self.k8s_client.get_pod_annotations(namespace, pod_name)
        last_update = annotations.get("resource-manager/last-update")
        
        # If we have a last update timestamp, check cooldown period
        if last_update:
            try:
                last_update_time = datetime.strptime(last_update, "%Y-%m-%dT%H:%M:%SZ")
                cooldown_end_time = last_update_time + timedelta(seconds=self.cooldown_period_seconds)
                
                if datetime.utcnow() < cooldown_end_time:
                    if logging.getLogger().isEnabledFor(logging.DEBUG):
                        remaining = cooldown_end_time - datetime.utcnow()
                        logging.debug(
                            f"Pod {namespace}/{pod_name} container {container_name} in cooldown period. "
                            f"{remaining.total_seconds():.0f} seconds remaining."
                        )
                    return
            except ValueError:
                logging.warning(f"Invalid timestamp format in pod annotation: {last_update}")
        
        # Calculate new memory request based on current usage
        new_memory_request = max(
            memory_usage * self.scale_down_usage_multiplier,
            self.min_request_memory
        )
        
        # Round to nearest integer
        new_memory_request = int(round(new_memory_request))
        
        # Calculate change percentage
        change_percentage = (current_request - new_memory_request) / current_request
        
        # Only scale down if the change is significant enough
        if change_percentage >= self.scale_down_min_diff:
            logging.info(
                f"Pod {namespace}/{pod_name} container {container_name} memory usage ratio: {memory_usage/current_request:.2f} "
                f"- scaling DOWN from {current_request:.0f}Mi to {new_memory_request}Mi (change: {change_percentage:.1%})"
            )
            
            # Update the resources
            self.k8s_client.patch_pod_resources(
                namespace=namespace,
                pod_name=pod_name,
                container_name=container_name,
                memory_request=new_memory_request
            )
        else:
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                logging.debug(
                    f"Pod {namespace}/{pod_name} container {container_name} - change too small "
                    f"({change_percentage:.1%}) to scale down"
                )


def main():
    # Configure logging with level control via environment variable
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)
    logging.basicConfig(level=numeric_level, format="%(asctime)s - %(levelname)s - %(message)s")
    
    logging.info(f"Starting resource manager with LOG_LEVEL={log_level}")
    
    # Create and run the resource manager
    manager = ResourceManager()
    manager.run()


if __name__ == "__main__":
    main()