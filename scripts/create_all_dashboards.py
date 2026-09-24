#!/usr/bin/env python3
import base64
import json
import os
import urllib.request

KIBANA_PORT = os.getenv("KIBANA_PORT", "15601")
KIBANA_URL = os.getenv("KIBANA_URL", f"http://localhost:{KIBANA_PORT}")
KIBANA_USER = os.getenv("KIBANA_USER", os.getenv("ELASTIC_USERNAME", "elastic"))
KIBANA_PASSWORD = os.getenv("KIBANA_PASSWORD", os.getenv("ELASTIC_PASSWORD", "BilginIT454"))
auth_token = base64.b64encode(f"{KIBANA_USER}:{KIBANA_PASSWORD}".encode("utf-8")).decode("utf-8")

def api_post(endpoint, data):
    req = urllib.request.Request(
        f"{KIBANA_URL}{endpoint}",
        data=json.dumps(data).encode("utf-8"),
        headers={
            "kbn-xsrf": "true",
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_token}"
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

print("[+] Creating Saved Searches...")

# 1. App Logs Stream Search
app_search = {
    "attributes": {
        "title": "Live Application Log Stream",
        "columns": ["service", "method", "url", "response_code", "latency_ms", "level"],
        "sort": [["@timestamp", "desc"]],
        "kibanaSavedObjectMeta": {
            "searchSourceJSON": json.dumps({
                "query": {"query": "", "language": "kuery"},
                "filter": [],
                "indexRefName": "kibanaSavedObjectMeta.searchSourceJSON.index"
            })
        }
    },
    "references": [
        {"name": "kibanaSavedObjectMeta.searchSourceJSON.index", "type": "index-pattern", "id": "app-logs-view"}
    ]
}
api_post("/api/saved_objects/search/app-logs-search?overwrite=true", app_search)

# 2. Security Log Stream Search
sec_search = {
    "attributes": {
        "title": "Live Security & SIEM Event Stream",
        "columns": ["service", "user", "client_ip", "event.action", "severity", "level", "message"],
        "sort": [["@timestamp", "desc"]],
        "kibanaSavedObjectMeta": {
            "searchSourceJSON": json.dumps({
                "query": {"query": "", "language": "kuery"},
                "filter": [],
                "indexRefName": "kibanaSavedObjectMeta.searchSourceJSON.index"
            })
        }
    },
    "references": [
        {"name": "kibanaSavedObjectMeta.searchSourceJSON.index", "type": "index-pattern", "id": "system-logs-view"}
    ]
}
api_post("/api/saved_objects/search/security-logs-search?overwrite=true", sec_search)

# 3. K8s Pod Logs Search
k8s_search = {
    "attributes": {
        "title": "Live Kubernetes Pod Events",
        "columns": ["kubernetes.namespace", "kubernetes.pod.name", "event.reason", "level", "message"],
        "sort": [["@timestamp", "desc"]],
        "kibanaSavedObjectMeta": {
            "searchSourceJSON": json.dumps({
                "query": {"query": "", "language": "kuery"},
                "filter": [],
                "indexRefName": "kibanaSavedObjectMeta.searchSourceJSON.index"
            })
        }
    },
    "references": [
        {"name": "kibanaSavedObjectMeta.searchSourceJSON.index", "type": "index-pattern", "id": "k8s-logs-view"}
    ]
}
api_post("/api/saved_objects/search/k8s-logs-search?overwrite=true", k8s_search)

# 4. CI/CD Build Search
cicd_search = {
    "attributes": {
        "title": "Live CI/CD Build Logs",
        "columns": ["ci.tool", "ci.pipeline_id", "ci.stage", "ci.status", "ci.duration_sec", "ci.branch"],
        "sort": [["@timestamp", "desc"]],
        "kibanaSavedObjectMeta": {
            "searchSourceJSON": json.dumps({
                "query": {"query": "", "language": "kuery"},
                "filter": [],
                "indexRefName": "kibanaSavedObjectMeta.searchSourceJSON.index"
            })
        }
    },
    "references": [
        {"name": "kibanaSavedObjectMeta.searchSourceJSON.index", "type": "index-pattern", "id": "cicd-logs-view"}
    ]
}
api_post("/api/saved_objects/search/cicd-logs-search?overwrite=true", cicd_search)

print("[✓] Saved searches created.")

# Helper to create Lens objects
def create_lens(lens_id, title, view_id, x_field, y_type, split_field=None, chart_type="bar_stacked"):
    layers = {
        "layer_1": {
            "columnOrder": ["col_x", "col_y"] if not split_field else ["col_x", "col_split", "col_y"],
            "columns": {
                "col_x": {
                    "dataType": "date" if x_field == "@timestamp" else "string",
                    "isBucketed": True,
                    "label": "Time" if x_field == "@timestamp" else x_field.split(".")[0].title(),
                    "operationType": "date_histogram" if x_field == "@timestamp" else "terms",
                    "params": {"interval": "auto"} if x_field == "@timestamp" else {"size": 8, "orderBy": {"type": "column", "columnId": "col_y"}},
                    "scale": "interval" if x_field == "@timestamp" else "ordinal",
                    "sourceField": x_field
                },
                "col_y": {
                    "dataType": "number",
                    "isBucketed": False,
                    "label": "Count",
                    "operationType": "count",
                    "scale": "ratio",
                    "sourceField": "___records___"
                }
            },
            "incompleteColumns": {}
        }
    }
    if split_field:
        layers["layer_1"]["columns"]["col_split"] = {
            "dataType": "string" if not split_field.startswith("response") else "number",
            "isBucketed": True,
            "label": split_field.split(".")[0].title(),
            "operationType": "terms",
            "params": {"size": 5, "orderBy": {"type": "column", "columnId": "col_y"}},
            "scale": "ordinal",
            "sourceField": split_field
        }
        
    lens = {
        "attributes": {
            "title": title,
            "visualizationType": "lnsXY",
            "state": {
                "datasourceStates": {"formBased": {"layers": layers}},
                "filters": [],
                "query": {"language": "kuery", "query": ""},
                "visualization": {
                    "preferredSeriesType": chart_type,
                    "axisTitlesVisibilitySettings": {"x": True, "yLeft": True, "yRight": True},
                    "gridlinesVisibilitySettings": {"x": True, "yLeft": True, "yRight": True},
                    "tickLabelsVisibilitySettings": {"x": True, "yLeft": True, "yRight": True},
                    "legend": {"isVisible": True, "legendSize": "auto", "position": "right"},
                    "valueLabels": "hide",
                    "fittingFunction": "None",
                    "yLeftExtent": {"mode": "full"},
                    "yRightExtent": {"mode": "full"},
                    "layers": [
                        {
                            "layerId": "layer_1",
                            "layerType": "data",
                            "seriesType": chart_type,
                            "accessors": ["col_y"],
                            "xAccessor": "col_x",
                            **({"splitAccessor": "col_split"} if split_field else {})
                        }
                    ]
                }
            }
        },
        "references": [
            {"id": view_id, "name": "indexpattern-datasource-current-indexpattern", "type": "index-pattern"},
            {"id": view_id, "name": "indexpattern-datasource-layer-layer_1", "type": "index-pattern"}
        ]
    }
    api_post(f"/api/saved_objects/lens/{lens_id}?overwrite=true", lens)

print("[+] Creating Visualizations for K8s, CI/CD, and Microservices...")
create_lens("k8s-events-over-time", "Kubernetes Events & Restarts Over Time", "k8s-logs-view", "@timestamp", "count", "event.reason.keyword", "bar_stacked")
create_lens("k8s-pod-namespace-split", "Log Volume by Namespace", "k8s-logs-view", "kubernetes.namespace.keyword", "count", None, "bar_horizontal")

create_lens("cicd-status-over-time", "Build Status Trends Over Time", "cicd-logs-view", "@timestamp", "count", "ci.status.keyword", "bar_stacked")
create_lens("cicd-stage-duration", "Build Executions by Pipeline Stage", "cicd-logs-view", "ci.stage.keyword", "count", None, "bar_horizontal")

create_lens("microservices-traffic", "Traffic Volume by Microservice", "app-logs-view", "@timestamp", "count", "service.keyword", "bar_stacked")

print("[✓] Visualizations created.")

# Helper to create a complete Dashboard
def create_dashboard(dash_id, title, desc, panels, references):
    dash = {
        "attributes": {
            "title": title,
            "description": desc,
            "panelsJSON": json.dumps(panels),
            "optionsJSON": json.dumps({"useMargins": True, "syncColors": True, "hidePanelTitles": False}),
            "timeRestore": False,
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({"query": {"language": "kuery", "query": ""}, "filter": []})
            }
        },
        "references": references
    }
    api_post(f"/api/saved_objects/dashboard/{dash_id}?overwrite=true", dash)
    print(f"[✓] Dashboard '{title}' created.")

# -------------------------------------------------------------
# Dashboard 1: [Kubernetes] Cluster & Pod Health Monitor
# -------------------------------------------------------------
create_dashboard(
    "k8s-cluster-pod-health",
    "[Kubernetes] Cluster & Pod Health Monitor",
    "Real-time monitoring of Kubernetes namespaces, OOMKilled events, and container logs",
    [
        {"version": "8.17.0", "type": "lens", "gridData": {"x": 0, "y": 0, "w": 30, "h": 14, "i": "1"}, "panelIndex": "1", "panelRefName": "panel_0"},
        {"version": "8.17.0", "type": "lens", "gridData": {"x": 30, "y": 0, "w": 18, "h": 14, "i": "2"}, "panelIndex": "2", "panelRefName": "panel_1"},
        {"version": "8.17.0", "type": "search", "gridData": {"x": 0, "y": 14, "w": 48, "h": 16, "i": "3"}, "panelIndex": "3", "panelRefName": "panel_2"}
    ],
    [
        {"name": "panel_0", "type": "lens", "id": "k8s-events-over-time"},
        {"name": "panel_1", "type": "lens", "id": "k8s-pod-namespace-split"},
        {"name": "panel_2", "type": "search", "id": "k8s-logs-search"}
    ]
)

# -------------------------------------------------------------
# Dashboard 2: [CI/CD] Jenkins & GitLab Pipeline Observability
# -------------------------------------------------------------
create_dashboard(
    "cicd-pipeline-performance",
    "[CI/CD] Jenkins & GitLab Pipeline Observability",
    "Continuous Integration & Deployment build performance, failure analysis, and stage metrics",
    [
        {"version": "8.17.0", "type": "lens", "gridData": {"x": 0, "y": 0, "w": 28, "h": 14, "i": "1"}, "panelIndex": "1", "panelRefName": "panel_0"},
        {"version": "8.17.0", "type": "lens", "gridData": {"x": 28, "y": 0, "w": 20, "h": 14, "i": "2"}, "panelIndex": "2", "panelRefName": "panel_1"},
        {"version": "8.17.0", "type": "search", "gridData": {"x": 0, "y": 14, "w": 48, "h": 16, "i": "3"}, "panelIndex": "3", "panelRefName": "panel_2"}
    ],
    [
        {"name": "panel_0", "type": "lens", "id": "cicd-status-over-time"},
        {"name": "panel_1", "type": "lens", "id": "cicd-stage-duration"},
        {"name": "panel_2", "type": "search", "id": "cicd-logs-search"}
    ]
)

# -------------------------------------------------------------
# Dashboard 3: [Security] SIEM & Threat Hunting Center
# -------------------------------------------------------------
create_dashboard(
    "security-siem-threat-center",
    "[Security] SIEM & Threat Hunting Center",
    "MITRE ATT&CK detection, SSH brute-force analysis, firewall drops, and live security audit logs",
    [
        {"version": "8.17.0", "type": "lens", "gridData": {"x": 0, "y": 0, "w": 48, "h": 14, "i": "1"}, "panelIndex": "1", "panelRefName": "panel_0"},
        {"version": "8.17.0", "type": "search", "gridData": {"x": 0, "y": 14, "w": 48, "h": 16, "i": "2"}, "panelIndex": "2", "panelRefName": "panel_1"}
    ],
    [
        {"name": "panel_0", "type": "lens", "id": "top-attackers-lens"},
        {"name": "panel_1", "type": "search", "id": "security-logs-search"}
    ]
)

# -------------------------------------------------------------
# Dashboard 4: [DevOps] Microservices & API Observability
# -------------------------------------------------------------
create_dashboard(
    "devops-microservices-observability",
    "[DevOps] Microservices & API Observability",
    "End-to-end distributed service health, request codes, latency, and live access stream",
    [
        {"version": "8.17.0", "type": "lens", "gridData": {"x": 0, "y": 0, "w": 28, "h": 14, "i": "1"}, "panelIndex": "1", "panelRefName": "panel_0"},
        {"version": "8.17.0", "type": "lens", "gridData": {"x": 28, "y": 0, "w": 20, "h": 14, "i": "2"}, "panelIndex": "2", "panelRefName": "panel_1"},
        {"version": "8.17.0", "type": "search", "gridData": {"x": 0, "y": 14, "w": 48, "h": 16, "i": "3"}, "panelIndex": "3", "panelRefName": "panel_2"}
    ],
    [
        {"name": "panel_0", "type": "lens", "id": "microservices-traffic"},
        {"name": "panel_1", "type": "lens", "id": "top-urls-lens"},
        {"name": "panel_2", "type": "search", "id": "app-logs-search"}
    ]
)

# -------------------------------------------------------------
# Dashboard 5: DevOps Observability & Security Dashboard (Updated Unified)
# -------------------------------------------------------------
create_dashboard(
    "devops-ops-overview",
    "DevOps Observability & Security Dashboard",
    "Unified production operations dashboard combining Application HTTP traffic, API endpoints, and Security incidents",
    [
        {"version": "8.17.0", "type": "lens", "gridData": {"x": 0, "y": 0, "w": 48, "h": 14, "i": "1"}, "panelIndex": "1", "panelRefName": "panel_0"},
        {"version": "8.17.0", "type": "lens", "gridData": {"x": 0, "y": 14, "w": 24, "h": 14, "i": "2"}, "panelIndex": "2", "panelRefName": "panel_1"},
        {"version": "8.17.0", "type": "lens", "gridData": {"x": 24, "y": 14, "w": 24, "h": 14, "i": "3"}, "panelIndex": "3", "panelRefName": "panel_2"},
        {"version": "8.17.0", "type": "search", "gridData": {"x": 0, "y": 28, "w": 48, "h": 16, "i": "4"}, "panelIndex": "4", "panelRefName": "panel_3"}
    ],
    [
        {"name": "panel_0", "type": "lens", "id": "http-status-codes-lens"},
        {"name": "panel_1", "type": "lens", "id": "top-urls-lens"},
        {"name": "panel_2", "type": "lens", "id": "top-attackers-lens"},
        {"name": "panel_3", "type": "search", "id": "app-logs-search"}
    ]
)

print("[✓] All 5 DevOps Dashboards and Visualizations have been created successfully!")
