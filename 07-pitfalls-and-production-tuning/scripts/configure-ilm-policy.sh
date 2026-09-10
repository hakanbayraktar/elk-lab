#!/usr/bin/env bash
set -euo pipefail

ES_URL="${ES_URL:-http://localhost:9200}"

echo "[+] Creating 7-Day Retention ILM Policy (devops_7day_retention)..."
curl -s -X PUT "${ES_URL}/_ilm/policy/devops_7day_retention" \
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
