#!/usr/bin/env bash
set -euo pipefail

ES_URL="${ES_URL:-http://localhost:9200}"
ES_USER="${ES_USER:-elastic}"
ES_PASSWORD="${ES_PASSWORD:-BilginIT454}"
CURL_CMD="curl -s -u ${ES_USER}:${ES_PASSWORD}"

echo "=================================================================="
echo "          Elasticsearch Diagnostic & Cluster Health Check         "
echo "=================================================================="

echo -e "\n[+] 1. Cluster Health Status:"
${CURL_CMD} "${ES_URL}/_cluster/health?pretty"

echo -e "\n[+] 2. Node Stats & JVM Memory Usage:"
${CURL_CMD} "${ES_URL}/_cat/nodes?v&h=name,ip,heap.percent,ram.percent,cpu,load_1m,node.role"

echo -e "\n[+] 3. Shard Allocation Summary:"
${CURL_CMD} "${ES_URL}/_cat/shards?v&h=index,shard,prirep,state,docs,store,unassigned.reason" | head -n 30

echo -e "\n[+] 4. Checking for Unassigned Shards:"
UNASSIGNED_COUNT=$(${CURL_CMD} "${ES_URL}/_cluster/health" | jq '.unassigned_shards // 0')
if [ "${UNASSIGNED_COUNT}" -gt 0 ]; then
  echo "    [!] Warning: ${UNASSIGNED_COUNT} unassigned shards detected!"
  echo "    Running allocation explain for the first unassigned shard:"
  ${CURL_CMD} -X POST "${ES_URL}/_cluster/allocation/explain?pretty"
else
  echo "    [✓] All shards are assigned."
fi

echo -e "\n[+] 5. Disk Watermark Limits & Disk Free Percent:"
${CURL_CMD} "${ES_URL}/_cat/allocation?v&h=node,shards,disk.indices,disk.used,disk.avail,disk.total,disk.percent"
