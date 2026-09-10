#!/usr/bin/env bash
set -euo pipefail

ES_URL="${ES_URL:-http://localhost:9200}"

echo "[+] Setting number_of_replicas to 0 for all indices (Single-node environment)..."
curl -s -X PUT "${ES_URL}/*/_settings" \
  -H 'Content-Type: application/json' \
  -d '{
    "index": {
      "number_of_replicas": 0
    }
  }' | jq .

echo "[+] Verifying cluster status (Target: GREEN):"
sleep 2
curl -s "${ES_URL}/_cluster/health?pretty" | grep status
