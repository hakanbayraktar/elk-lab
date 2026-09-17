#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ES_URL="${ES_URL:-http://localhost:9200}"
KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"

echo "=================================================================="
echo "    🚀 Elastic Stack (ELK 8.x) Full Lab Automated Bootstrap       "
echo "=================================================================="

# 1. Check Kernel Parameter
echo "[+] 1. Checking Linux vm.max_map_count..."
if command -v sysctl >/dev/null 2>&1; then
  CURRENT_MAP=$(sysctl -n vm.max_map_count 2>/dev/null || echo "262144")
  if [ "${CURRENT_MAP}" -lt 262144 ]; then
    echo "    [!] Warning: vm.max_map_count is ${CURRENT_MAP}. Setting to 262144..."
    sudo sysctl -w vm.max_map_count=262144 2>/dev/null || true
  else
    echo "    [✓] vm.max_map_count is sufficient (${CURRENT_MAP})."
  fi
fi

# 2. Start Core ELK Stack
echo "[+] 2. Starting Core ELK Stack (Elasticsearch, Logstash, Kibana)..."
docker compose -f "${SCRIPT_DIR}/00-elk-core-stack/docker-compose.yml" up -d

# 3. Start Demo Microservice Apps
echo "[+] 3. Starting Demo Microservices (Nginx :8081 & Node API :3001)..."
docker compose -f "${SCRIPT_DIR}/02-workspace-apps-logging/sample-apps/docker-compose.apps.yml" up -d

# 4. Wait for Elasticsearch & Kibana Health
echo "[+] 4. Waiting for Elasticsearch & Kibana to become available..."
until curl -s "${ES_URL}/_cluster/health" | grep -q '"status"'; do
  echo "    Waiting for Elasticsearch (:9200)..."
  sleep 3
done
echo "    [✓] Elasticsearch is healthy."

until curl -s "${KIBANA_URL}/api/status" | grep -q '"level":"available"'; do
  echo "    Waiting for Kibana (:5601)..."
  sleep 4
done
echo "    [✓] Kibana is available."

# 5. Populate Sample Datasets
echo "[+] 5. Ingesting Rich Multi-Cloud & DevOps Datasets (K8s, CI/CD, SIEM, Microservices)..."
if [ -f "${SCRIPT_DIR}/scripts/generate_rich_devops_datasets.py" ]; then
  python3 "${SCRIPT_DIR}/scripts/generate_rich_devops_datasets.py"
fi

# 6. Generate Live Application Traffic & Ship Logs
echo "[+] 6. Generating Live Application Traffic to Nginx & Node.js API..."
if [ -f "${SCRIPT_DIR}/02-workspace-apps-logging/sample-apps/generate-and-ship-traffic.sh" ]; then
  "${SCRIPT_DIR}/02-workspace-apps-logging/sample-apps/generate-and-ship-traffic.sh" 50 >/dev/null 2>&1 || true
fi

# 7. Ingest Security Attack & Threat Scenarios
echo "[+] 7. Injecting SIEM & Threat Hunting Security Events..."
if [ -f "${SCRIPT_DIR}/06-siem-and-security-analytics/scripts/simulate-attacks.sh" ]; then
  "${SCRIPT_DIR}/06-siem-and-security-analytics/scripts/simulate-attacks.sh" 10 >/dev/null 2>&1 || true
fi

# 8. Setup Data Views, Lens Visualizations, Saved Searches & 8 Dashboards
echo "[+] 8. Configuring Data Views, Lens Visualizations & 8 Dashboards in Kibana..."
"${SCRIPT_DIR}/05-kibana-dashboards-and-kql/scripts/import-dashboards.sh"

echo ""
echo "=================================================================="
echo "    🎉 ELK Lab Setup Completed Successfully! (All in Code)        "
echo "=================================================================="
echo "  Kibana Dashboard Hub:          ${KIBANA_URL}/app/dashboards"
echo "  Kibana Discover Stream:        ${KIBANA_URL}/app/discover"
echo "  ----------------------------------------------------------------"
echo "  1. DevOps Unified Dashboard:   ${KIBANA_URL}/app/dashboards#/view/devops-ops-overview"
echo "  2. Microservices & API:        ${KIBANA_URL}/app/dashboards#/view/devops-microservices-observability"
echo "  3. Kubernetes Cluster & Pods:  ${KIBANA_URL}/app/dashboards#/view/k8s-cluster-pod-health"
echo "  4. CI/CD Pipeline Performance: ${KIBANA_URL}/app/dashboards#/view/cicd-pipeline-performance"
echo "  5. Security & Threat Hunting:  ${KIBANA_URL}/app/dashboards#/view/security-siem-threat-center"
echo "  6. Official Web Logs Traffic:  ${KIBANA_URL}/app/dashboards#/view/edf84fe0-e1a0-11e7-b6d5-4dc382ef7f5b"
echo "  7. Official E-Commerce Orders: ${KIBANA_URL}/app/dashboards#/view/722b74f0-b882-11e8-a6d9-e546fe2bba5f"
echo "  8. Official Global Flights:    ${KIBANA_URL}/app/dashboards#/view/7adfa750-4c81-11e8-b3d7-01146121b73d"
echo "=================================================================="
