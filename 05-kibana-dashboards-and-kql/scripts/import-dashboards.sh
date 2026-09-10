#!/usr/bin/env bash
set -euo pipefail

KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"

echo "[+] Checking Kibana status at ${KIBANA_URL}..."
until curl -s "${KIBANA_URL}/api/status" | grep -q '"level":"available"'; do
  echo "    Waiting for Kibana to be ready..."
  sleep 3
done
echo "[✓] Kibana is available."

echo "[+] 1. Creating / updating Data Views for ELK Labs..."
for view in \
  '{"data_view":{"id":"app-logs-view","title":"app-logs-*","name":"Application Logs (Nginx & API)","timeFieldName":"@timestamp"}}' \
  '{"data_view":{"id":"filebeat-view","title":"filebeat-*","name":"Filebeat Infrastructure (Docker & K8s)","timeFieldName":"@timestamp"}}' \
  '{"data_view":{"id":"system-logs-view","title":"system-logs-*","name":"Linux System Logs (Auth & Syslog)","timeFieldName":"@timestamp"}}'; do

  curl -s -X POST "${KIBANA_URL}/api/data_views/data_view" \
    -H 'kbn-xsrf: true' \
    -H 'Content-Type: application/json' \
    -d "${view}" > /dev/null 2>&1 || true
done

echo "[+] 2. Creating clean DevOps Observability & Security Dashboard..."
curl -s -X POST "${KIBANA_URL}/api/saved_objects/dashboard/devops-ops-overview?overwrite=true" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{
    "attributes": {
      "title": "DevOps Observability & Security Dashboard",
      "description": "Unified dashboard for system, application, and security metrics",
      "panelsJSON": "[]",
      "optionsJSON": "{\"useMargins\":true,\"syncColors\":true,\"hidePanelTitles\":false}",
      "timeRestore": false
    },
    "references": []
  }' > /dev/null 2>&1 || true

echo "[+] 3. Loading Official Web Traffic Visual Dashboards..."
curl -s -X POST "${KIBANA_URL}/api/sample_data/logs" -H 'kbn-xsrf: true' > /dev/null 2>&1 || true

echo "[✓] Setup completed successfully."
echo "=================================================================="
echo "  Kibana Discover:  ${KIBANA_URL}/app/discover"
echo "  Kibana Dashboard: ${KIBANA_URL}/app/dashboards"
echo "=================================================================="
