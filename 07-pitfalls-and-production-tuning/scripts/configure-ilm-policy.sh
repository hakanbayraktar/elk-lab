#!/usr/bin/env bash
set -euo pipefail

ES_URL="${ES_URL:-http://localhost:9200}"
ES_USER="${ES_USER:-elastic}"
ES_PASSWORD="${ES_PASSWORD:-BilginIT454}"
CURL_CMD="curl -s -u ${ES_USER}:${ES_PASSWORD}"

echo "[+] Creating 7-Day Retention ILM Policy (devops_7day_retention)..."
${CURL_CMD} -X PUT "${ES_URL}/_ilm/policy/devops_7day_retention" \
  -H 'Content-Type: application/json' \
  -d '{
    "policy": {
      "phases": {
        "hot": {
          "actions": {
            "rollover": {
              "max_primary_shard_size": "30gb",
              "max_age": "1d"
            }
          }
        },
        "delete": {
          "min_age": "7d",
          "actions": {
            "delete": {}
          }
        }
      }
    }
  }' | jq .

echo "[✓] ILM policy configured successfully."
