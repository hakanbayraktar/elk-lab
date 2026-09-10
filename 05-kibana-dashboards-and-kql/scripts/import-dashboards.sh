#!/usr/bin/env bash
set -euo pipefail

KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"

echo "[+] Checking Kibana status at ${KIBANA_URL}..."
until curl -s "${KIBANA_URL}/api/status" | grep -q '"level":"available"'; do
  echo "    Waiting for Kibana to be ready..."
  sleep 3
done
echo "[✓] Kibana is available."

echo "[+] 1. Installing Official Sample Logs & Dashboards..."
curl -s -X POST "${KIBANA_URL}/api/sample_data/logs" -H 'kbn-xsrf: true' > /dev/null 2>&1 || true

echo "[+] 2. Creating / updating Data Views for ELK Labs..."
for view in \
  '{"data_view":{"id":"app-logs-view","title":"app-logs-*","name":"Application Logs (Nginx & API)","timeFieldName":"@timestamp"}}' \
  '{"data_view":{"id":"filebeat-view","title":"filebeat-*","name":"Filebeat Infrastructure (Docker & K8s)","timeFieldName":"@timestamp"}}' \
  '{"data_view":{"id":"system-logs-view","title":"system-logs-*","name":"Linux System Logs (Auth & Syslog)","timeFieldName":"@timestamp"}}'; do

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
                "columnOrder": ["col_x", "col_y", "col_split"],
                "columns": {
                  "col_x": {"dataType": "date", "isBucketed": true, "label": "Timestamp", "operationType": "date_histogram", "params": {"interval": "auto"}, "scale": "interval", "sourceField": "@timestamp"},
                  "col_y": {"dataType": "number", "isBucketed": false, "label": "Count of logs", "operationType": "count", "scale": "ratio", "sourceField": "___records___"},
                  "col_split": {"dataType": "number", "isBucketed": true, "label": "response_code", "operationType": "terms", "params": {"size": 5, "orderBy": {"type": "column", "columnId": "col_y"}}, "scale": "ordinal", "sourceField": "response_code"}
                }
              }
            }
          }
        },
        "visualization": {
          "preferredSeriesType": "bar_stacked",
          "layers": [{"layerId": "layer_1", "accessors": ["col_y"], "xAccessor": "col_x", "splitAccessor": "col_split", "seriesType": "bar_stacked", "layerType": "data"}]
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
                  "col_x": {"dataType": "string", "isBucketed": true, "label": "URL Path", "operationType": "terms", "params": {"size": 8, "orderBy": {"type": "column", "columnId": "col_y"}}, "scale": "ordinal", "sourceField": "url"},
                  "col_y": {"dataType": "number", "isBucketed": false, "label": "Requests", "operationType": "count", "scale": "ratio", "sourceField": "___records___"}
                }
              }
            }
          }
        },
        "visualization": {
          "preferredSeriesType": "bar_horizontal",
          "layers": [{"layerId": "layer_1", "accessors": ["col_y"], "xAccessor": "col_x", "seriesType": "bar_horizontal", "layerType": "data"}]
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
                  "col_x": {"dataType": "string", "isBucketed": true, "label": "Attacker IP", "operationType": "terms", "params": {"size": 5, "orderBy": {"type": "column", "columnId": "col_y"}}, "scale": "ordinal", "sourceField": "client_ip"},
                  "col_y": {"dataType": "number", "isBucketed": false, "label": "Failed Logins", "operationType": "count", "scale": "ratio", "sourceField": "___records___"}
                }
              }
            }
          }
        },
        "visualization": {
          "preferredSeriesType": "bar_horizontal",
          "layers": [{"layerId": "layer_1", "accessors": ["col_y"], "xAccessor": "col_x", "seriesType": "bar_horizontal", "layerType": "data"}]
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

echo "[✓] Setup completed successfully."
echo "=================================================================="
echo "  Live Custom Dashboard:   ${KIBANA_URL}/app/dashboards#/view/devops-ops-overview"
echo "  Official Web Dashboard:  ${KIBANA_URL}/app/dashboards#/view/edf84fe0-e1a0-11e7-b6d5-4dc382ef7f5b"
echo "  Kibana Discover Stream:  ${KIBANA_URL}/app/discover"
echo "=================================================================="
