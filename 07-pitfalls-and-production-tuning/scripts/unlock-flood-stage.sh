#!/usr/bin/env bash
set -euo pipefail

ES_URL="${ES_URL:-http://localhost:9200}"

echo "[+] Removing read_only_allow_delete block on all indices..."
curl -s -X PUT "${ES_URL}/*/_settings" \
  -H 'Content-Type: application/json' \
  -d '{
    "index.blocks.read_only_allow_delete": null
  }' | jq .

echo "[✓] Cluster write lock released. New documents can now be indexed."
