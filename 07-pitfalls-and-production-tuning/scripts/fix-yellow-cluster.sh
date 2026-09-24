#!/usr/bin/env bash
set -euo pipefail

ES_URL="${ES_URL:-http://localhost:9200}"
ES_USER="${ES_USER:-elastic}"
ES_PASSWORD="${ES_PASSWORD:-BilginIT454}"
CURL_CMD="curl -s -u ${ES_USER}:${ES_PASSWORD}"

echo "[+] Setting number_of_replicas to 0 for all indices (Single-node environment)..."
${CURL_CMD} -X PUT "${ES_URL}/*/_settings" \
  -H 'Content-Type: application/json' \
  -d '{
    "index": {
      "number_of_replicas": 0
    }
  }' | jq .

echo "[+] Verifying cluster status (Target: GREEN):"
sleep 2
${CURL_CMD} "${ES_URL}/_cluster/health?pretty" | grep status
