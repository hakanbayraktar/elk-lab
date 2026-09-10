#!/usr/bin/env bash
set -euo pipefail

KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"

echo "[+] Checking Kibana status at ${KIBANA_URL}..."
until curl -s "${KIBANA_URL}/api/status" | grep -q '"level":"available"'; do
  echo "    Waiting for Kibana to be ready..."
  sleep 3
done
echo "[✓] Kibana is available."

echo "[+] 1. Creating / updating Data Views..."
for view in \
  '{"data_view":{"id":"app-logs-view","title":"app-logs-*","name":"Application Logs (Nginx & API)","timeFieldName":"@timestamp"}}' \
  '{"data_view":{"id":"filebeat-view","title":"filebeat-*","name":"Filebeat Infrastructure (Docker & K8s)","timeFieldName":"@timestamp"}}' \
  '{"data_view":{"id":"system-logs-view","title":"system-logs-*","name":"Linux System Logs (Auth & Syslog)","timeFieldName":"@timestamp"}}'; do

  curl -s -X POST "${KIBANA_URL}/api/data_views/data_view" \
    -H 'kbn-xsrf: true' \
    -H 'Content-Type: application/json' \
    -d "${view}" > /dev/null 2>&1 || true
done

echo "[+] 2. Creating Saved Searches for Dashboard Panels..."
# Panel 1: SSH Brute Force
curl -s -X POST "${KIBANA_URL}/api/saved_objects/search/ssh-bruteforce-search?overwrite=true" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{
    "attributes": {
      "title": "Security: SSH Brute Force Events",
      "description": "Failed password attempts by attacker IP",
      "columns": ["@timestamp", "client_ip", "user", "message"],
      "sort": [["@timestamp", "desc"]],
      "kibanaSavedObjectMeta": {
        "searchSourceJSON": "{\"query\":{\"query\":\"\",\"language\":\"kuery\"},\"filter\":[],\"indexRefName\":\"kibanaSavedObjectMeta.searchSourceJSON.index\"}"
      }
    },
    "references": [
      {
        "name": "kibanaSavedObjectMeta.searchSourceJSON.index",
        "type": "index-pattern",
        "id": "system-logs-view"
      }
    ]
  }' > /dev/null 2>&1 || true

# Panel 2: Web Attacks & Scans
curl -s -X POST "${KIBANA_URL}/api/saved_objects/search/web-attack-search?overwrite=true" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{
    "attributes": {
      "title": "Security: Web Application Attacks & Scans",
      "description": "Suspicious HTTP requests (Path Traversal, SQLi)",
      "columns": ["@timestamp", "client_ip", "method", "url", "response_code"],
      "sort": [["@timestamp", "desc"]],
      "kibanaSavedObjectMeta": {
        "searchSourceJSON": "{\"query\":{\"query\":\"\",\"language\":\"kuery\"},\"filter\":[],\"indexRefName\":\"kibanaSavedObjectMeta.searchSourceJSON.index\"}"
      }
    },
    "references": [
      {
        "name": "kibanaSavedObjectMeta.searchSourceJSON.index",
        "type": "index-pattern",
        "id": "app-logs-view"
      }
    ]
  }' > /dev/null 2>&1 || true

echo "[+] 3. Creating Unified Observability & Security Dashboard..."
curl -s -X POST "${KIBANA_URL}/api/saved_objects/dashboard/devops-ops-overview?overwrite=true" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{
    "attributes": {
      "title": "DevOps Observability & Security Dashboard",
      "description": "Unified dashboard for system, application, and security metrics",
      "panelsJSON": "[{\"version\":\"8.17.0\",\"type\":\"search\",\"gridData\":{\"x\":0,\"y\":0,\"w\":24,\"h\":15,\"i\":\"1\"},\"panelIndex\":\"1\",\"panelRefName\":\"panel_0\"},{\"version\":\"8.17.0\",\"type\":\"search\",\"gridData\":{\"x\":24,\"y\":0,\"w\":24,\"h\":15,\"i\":\"2\"},\"panelIndex\":\"2\",\"panelRefName\":\"panel_1\"}]",
      "optionsJSON": "{\"useMargins\":true,\"syncColors\":true,\"hidePanelTitles\":false}",
      "timeRestore": false
    },
    "references": [
      {
        "name": "panel_0",
        "type": "search",
        "id": "ssh-bruteforce-search"
      },
      {
        "name": "panel_1",
        "type": "search",
        "id": "web-attack-search"
      }
    ]
  }' > /dev/null 2>&1 || true

echo "[✓] Data views, panels and dashboard created successfully."
echo "[✓] Open the dashboard directly in your browser: ${KIBANA_URL}/app/dashboards#/view/devops-ops-overview"
