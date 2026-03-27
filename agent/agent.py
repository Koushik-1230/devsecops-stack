import requests
import time
import os 
from kubernetes import client, config

config.load_incluster_config()
metrics_api = client.CustomObjectsApi()

BACKEND_URL = os.getenv("BACKEND_URL", "https://super-potato-jx4p9xq9p4rf549q-8000.app.github.dev/ingest")
CLUSTER_TOKEN = os.getenv("CLUSTER_TOKEN", "cluster123")
CLUSTER_NAME = os.getenv("CLUSTER_NAME", "Cluster 1")
PROM_URL = os.getenv("PROM_URL", "http://kube-prometheus-stack-prometheus:9090")
INTERVAL = int(os.getenv("INTERVAL", "15"))

def get_k8s_metrics():
    try:
        nodes = metrics_api.list_cluster_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            plural="nodes"
        )

        result = []

        for node in nodes.get("items", []):
            node_name = node["metadata"]["name"]
            cpu_usage = node["usage"]["cpu"]
            mem_usage = node["usage"]["memory"]
            result.append({
                "node": node_name,
                "cpu": cpu_usage,
                "memory": mem_usage
            })
        return result
    except Exception as e:
        print(f"Error fetching k8s metrics: {e}")
        return []
    
def query_prometheus(query):
    try:
        response = requests.get(f"{PROM_URL}/api/v1/query", params={"query": query}, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("result", [])
    except Exception as e:
        print(f"Error querying Prometheus: {e}")
        return []
    
def get_prom_metrics():
    return {
        "cpu_usage": query_prometheus("rate(container_cpu_usage_seconds_total[5m])"),
        "mem_usage": query_prometheus("container_memory_usage_bytes")
    }

def collect_metrics():
    return {
        "cluster": CLUSTER_NAME,
        "k8s_nodes": get_k8s_metrics(),
        "prometheus": get_prom_metrics(),
        "timestamp": int(time.time())
    }

def send_metrics():
    data = collect_metrics()
    try:
        res = requests.post(
            BACKEND_URL,
            json=data,
            headers={
                "Authorization": f"Bearer {CLUSTER_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=5
        )
        print(f"Sent metrics: {res.status_code}")
    except Exception as e:
        print(f"Error sending metrics: {e}")

while True:
    send_metrics()
    time.sleep(INTERVAL)