#!/usr/bin/env bash
set -euo pipefail

ES_URL="${ES_URL:-http://localhost:9200}"
ES_USER="${ES_USER:-elastic}"
ES_PASSWORD="${ES_PASSWORD:-BilginIT454}"
CURL_CMD="curl -s -u ${ES_USER}:${ES_PASSWORD}"

echo "[+] Removing read_only_allow_delete block on all indices..."
${CURL_CMD} -X PUT "${ES_URL}/*/_settings" \
  -H 'Content-Type: application/json' \
  -d '{
    "index.blocks.read_only_allow_delete": null
  }' | jq .

echo "[✓] Cluster write lock released. New documents can now be indexed."
