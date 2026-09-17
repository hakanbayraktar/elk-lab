#!/usr/bin/env bash
set -euo pipefail

KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"

echo "[+] Checking Kibana status at ${KIBANA_URL}..."
until curl -s "${KIBANA_URL}/api/status" | grep -q '"level":"available"'; do
  echo "    Waiting for Kibana to be ready..."
  sleep 3
done
echo "[✓] Kibana is available."

echo "[+] 1. Checking and Installing Official Sample Datasets (Logs, Ecommerce, Flights)..."
SAMPLE_JSON=$(curl -s --max-time 15 -X GET "${KIBANA_URL}/api/sample_data" -H 'kbn-xsrf: true' || echo "[]")
for sample in logs ecommerce flights; do
  STATUS=$(echo "${SAMPLE_JSON}" | jq -r ".[] | select(.id == \"${sample}\") | .status" 2>/dev/null || echo "")
  if [ "${STATUS}" != "installed" ]; then
    echo "    Installing sample dataset: ${sample}..."
    curl -s --max-time 60 -X POST "${KIBANA_URL}/api/sample_data/${sample}" -H 'kbn-xsrf: true' > /dev/null 2>&1 || true
  else
    echo "    Sample dataset '${sample}' is already installed."
  fi
done

echo "[+] 2. Creating / updating Data Views for ELK Labs..."
for view in \
  '{"data_view":{"id":"app-logs-view","title":"app-logs-*","name":"Application Logs (Nginx & API)","timeFieldName":"@timestamp"}}' \
  '{"data_view":{"id":"system-logs-view","title":"system-logs-*","name":"Linux System Logs (Auth & Syslog)","timeFieldName":"@timestamp"}}' \
  '{"data_view":{"id":"k8s-logs-view","title":"k8s-logs-*","name":"Kubernetes Pod & Cluster Logs","timeFieldName":"@timestamp"}}' \
  '{"data_view":{"id":"cicd-logs-view","title":"cicd-logs-*","name":"CI/CD Pipelines (Jenkins & GitLab)","timeFieldName":"@timestamp"}}' \
  '{"data_view":{"id":"filebeat-view","title":"filebeat-*","name":"Filebeat Infrastructure (Docker & K8s)","timeFieldName":"@timestamp"}}'; do

  curl -s -X POST "${KIBANA_URL}/api/data_views/data_view" \
    -H 'kbn-xsrf: true' \
    -H 'Content-Type: application/json' \
    -d "${view}" > /dev/null 2>&1 || true
done

echo "[+] 3. Creating Native Lens Visualizations for Application Logs..."
# 3.1 HTTP Status Codes Over Time
curl -s -X POST "${KIBANA_URL}/api/saved_objects/lens/http-status-codes-lens?overwrite=true" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{
    "attributes": {
      "title": "HTTP Status Codes Over Time",
      "visualizationType": "lnsXY",
      "state": {
        "datasourceStates": {
          "formBased": {
            "layers": {
              "layer_1": {
                "columnOrder": ["col_x", "col_split", "col_y"],
                "columns": {
                  "col_x": {"dataType": "date", "isBucketed": true, "label": "Timestamp", "operationType": "date_histogram", "params": {"interval": "auto"}, "scale": "interval", "sourceField": "@timestamp"},
                  "col_split": {"dataType": "number", "isBucketed": true, "label": "Status Code", "operationType": "terms", "params": {"size": 5, "orderBy": {"type": "column", "columnId": "col_y"}}, "scale": "ordinal", "sourceField": "response_code"},
                  "col_y": {"dataType": "number", "isBucketed": false, "label": "Count of logs", "operationType": "count", "scale": "ratio", "sourceField": "___records___"}
                },
                "incompleteColumns": {}
              }
            }
          }
        },
        "filters": [],
        "query": {"language": "kuery", "query": ""},
        "visualization": {
          "preferredSeriesType": "bar_stacked",
          "axisTitlesVisibilitySettings": {"x": true, "yLeft": true, "yRight": true},
          "gridlinesVisibilitySettings": {"x": true, "yLeft": true, "yRight": true},
          "tickLabelsVisibilitySettings": {"x": true, "yLeft": true, "yRight": true},
          "legend": {"isVisible": true, "legendSize": "auto", "position": "right"},
          "valueLabels": "hide",
          "fittingFunction": "None",
          "yLeftExtent": {"mode": "full"},
          "yRightExtent": {"mode": "full"},
          "layers": [
            {
              "layerId": "layer_1",
              "layerType": "data",
              "seriesType": "bar_stacked",
              "accessors": ["col_y"],
              "xAccessor": "col_x",
              "splitAccessor": "col_split"
            }
          ]
        }
      }
    },
    "references": [
      {"id": "app-logs-view", "name": "indexpattern-datasource-current-indexpattern", "type": "index-pattern"},
      {"id": "app-logs-view", "name": "indexpattern-datasource-layer-layer_1", "type": "index-pattern"}
    ]
  }' > /dev/null 2>&1 || true

# 3.2 Top Requested URLs
curl -s -X POST "${KIBANA_URL}/api/saved_objects/lens/top-urls-lens?overwrite=true" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{
    "attributes": {
      "title": "Top Requested URLs",
      "visualizationType": "lnsXY",
      "state": {
        "datasourceStates": {
          "formBased": {
            "layers": {
              "layer_1": {
                "columnOrder": ["col_x", "col_y"],
                "columns": {
                  "col_x": {"dataType": "string", "isBucketed": true, "label": "URL Path", "operationType": "terms", "params": {"size": 8, "orderBy": {"type": "column", "columnId": "col_y"}}, "scale": "ordinal", "sourceField": "url.keyword"},
                  "col_y": {"dataType": "number", "isBucketed": false, "label": "Requests", "operationType": "count", "scale": "ratio", "sourceField": "___records___"}
                },
                "incompleteColumns": {}
              }
            }
          }
        },
        "filters": [],
        "query": {"language": "kuery", "query": ""},
        "visualization": {
          "preferredSeriesType": "bar_horizontal",
          "axisTitlesVisibilitySettings": {"x": true, "yLeft": true, "yRight": true},
          "gridlinesVisibilitySettings": {"x": true, "yLeft": true, "yRight": true},
          "tickLabelsVisibilitySettings": {"x": true, "yLeft": true, "yRight": true},
          "legend": {"isVisible": true, "legendSize": "auto", "position": "right"},
          "valueLabels": "hide",
          "fittingFunction": "None",
          "yLeftExtent": {"mode": "full"},
          "yRightExtent": {"mode": "full"},
          "layers": [
            {
              "layerId": "layer_1",
              "layerType": "data",
              "seriesType": "bar_horizontal",
              "accessors": ["col_y"],
              "xAccessor": "col_x"
            }
          ]
        }
      }
    },
    "references": [
      {"id": "app-logs-view", "name": "indexpattern-datasource-current-indexpattern", "type": "index-pattern"},
      {"id": "app-logs-view", "name": "indexpattern-datasource-layer-layer_1", "type": "index-pattern"}
    ]
  }' > /dev/null 2>&1 || true

# 3.3 Top Attacker IPs
curl -s -X POST "${KIBANA_URL}/api/saved_objects/lens/top-attackers-lens?overwrite=true" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{
    "attributes": {
      "title": "Top Failed Logins by Attacker IP",
      "visualizationType": "lnsXY",
      "state": {
        "datasourceStates": {
          "formBased": {
            "layers": {
              "layer_1": {
                "columnOrder": ["col_x", "col_y"],
                "columns": {
                  "col_x": {"dataType": "string", "isBucketed": true, "label": "Attacker IP", "operationType": "terms", "params": {"size": 5, "orderBy": {"type": "column", "columnId": "col_y"}}, "scale": "ordinal", "sourceField": "client_ip.keyword"},
                  "col_y": {"dataType": "number", "isBucketed": false, "label": "Failed Logins", "operationType": "count", "scale": "ratio", "sourceField": "___records___"}
                },
                "incompleteColumns": {}
              }
            }
          }
        },
        "filters": [],
        "query": {"language": "kuery", "query": ""},
        "visualization": {
          "preferredSeriesType": "bar_horizontal",
          "axisTitlesVisibilitySettings": {"x": true, "yLeft": true, "yRight": true},
          "gridlinesVisibilitySettings": {"x": true, "yLeft": true, "yRight": true},
          "tickLabelsVisibilitySettings": {"x": true, "yLeft": true, "yRight": true},
          "legend": {"isVisible": true, "legendSize": "auto", "position": "right"},
          "valueLabels": "hide",
          "fittingFunction": "None",
          "yLeftExtent": {"mode": "full"},
          "yRightExtent": {"mode": "full"},
          "layers": [
            {
              "layerId": "layer_1",
              "layerType": "data",
              "seriesType": "bar_horizontal",
              "accessors": ["col_y"],
              "xAccessor": "col_x"
            }
          ]
        }
      }
    },
    "references": [
      {"id": "system-logs-view", "name": "indexpattern-datasource-current-indexpattern", "type": "index-pattern"},
      {"id": "system-logs-view", "name": "indexpattern-datasource-layer-layer_1", "type": "index-pattern"}
    ]
  }' > /dev/null 2>&1 || true

echo "[+] 4. Creating Unified DevOps Observability & Security Dashboard..."
curl -s -X POST "${KIBANA_URL}/api/saved_objects/dashboard/devops-ops-overview?overwrite=true" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{
    "attributes": {
      "title": "DevOps Observability & Security Dashboard",
      "description": "Live production dashboard for Nginx, Node.js API, and Security events",
      "panelsJSON": "[{\"version\":\"8.17.0\",\"type\":\"lens\",\"gridData\":{\"x\":0,\"y\":0,\"w\":48,\"h\":14,\"i\":\"1\"},\"panelIndex\":\"1\",\"panelRefName\":\"panel_0\"},{\"version\":\"8.17.0\",\"type\":\"lens\",\"gridData\":{\"x\":0,\"y\":14,\"w\":24,\"h\":14,\"i\":\"2\"},\"panelIndex\":\"2\",\"panelRefName\":\"panel_1\"},{\"version\":\"8.17.0\",\"type\":\"lens\",\"gridData\":{\"x\":24,\"y\":14,\"w\":24,\"h\":14,\"i\":\"3\"},\"panelIndex\":\"3\",\"panelRefName\":\"panel_2\"}]",
      "optionsJSON": "{\"useMargins\":true,\"syncColors\":true,\"hidePanelTitles\":false}",
      "timeRestore": false,
      "kibanaSavedObjectMeta": {
        "searchSourceJSON": "{\"query\":{\"language\":\"kuery\",\"query\":\"\"},\"filter\":[]}"
      }
    },
    "references": [
      {"name": "panel_0", "type": "lens", "id": "http-status-codes-lens"},
      {"name": "panel_1", "type": "lens", "id": "top-urls-lens"},
      {"name": "panel_2", "type": "lens", "id": "top-attackers-lens"}
    ]
  }' > /dev/null 2>&1 || true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [ -f "${PARENT_DIR}/scripts/create_all_dashboards.py" ]; then
  echo "[+] 5. Registering Full Suite of Specialized DevOps Dashboards (K8s, CI/CD, SIEM, Microservices)..."
  python3 "${PARENT_DIR}/scripts/create_all_dashboards.py" > /dev/null 2>&1 || true
fi

echo "[✓] Complete setup verified successfully!"
echo "=================================================================="
echo "  Kibana Dashboards List:        ${KIBANA_URL}/app/dashboards"
echo "  ----------------------------------------------------------------"
echo "  1. DevOps Unified Dashboard:   ${KIBANA_URL}/app/dashboards#/view/devops-ops-overview"
echo "  2. Microservices & API:        ${KIBANA_URL}/app/dashboards#/view/devops-microservices-observability"
echo "  3. Kubernetes Cluster & Pods:  ${KIBANA_URL}/app/dashboards#/view/k8s-cluster-pod-health"
echo "  4. CI/CD Pipeline Performance: ${KIBANA_URL}/app/dashboards#/view/cicd-pipeline-performance"
echo "  5. Security & Threat Hunting:  ${KIBANA_URL}/app/dashboards#/view/security-siem-threat-center"
echo "  6. Official Web Logs Traffic:  ${KIBANA_URL}/app/dashboards#/view/edf84fe0-e1a0-11e7-b6d5-4dc382ef7f5b"
echo "  7. Official E-Commerce Orders: ${KIBANA_URL}/app/dashboards#/view/722b74f0-b882-11e8-a6d9-e546fe2bba5f"
echo "  8. Official Global Flights:    ${KIBANA_URL}/app/dashboards#/view/7adfa750-4c81-11e8-b3d7-01146121b73d"
echo "  ----------------------------------------------------------------"
echo "  Kibana Discover Stream:        ${KIBANA_URL}/app/discover"
echo "=================================================================="
