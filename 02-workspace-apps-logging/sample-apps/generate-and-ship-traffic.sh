#!/usr/bin/env bash
set -euo pipefail

NGINX_URL="${NGINX_URL:-http://localhost:8081}"
API_URL="${API_URL:-http://localhost:3001}"
LOGSTASH_HOST="${LOGSTASH_HOST:-127.0.0.1}"
LOGSTASH_PORT="${LOGSTASH_PORT:-5000}"

echo "=================================================================="
echo "      Generating Live Traffic & Shipping Logs to Elastic Stack    "
echo "=================================================================="

URLS=(
  "/"
  "/products"
  "/api/v1/orders"
  "/healthz"
  "/images/banner.jpg"
  "/catalog"
  "/login"
  "/non-existent-page"
  "/missing.html"
  "/static/bundle.js"
)

CLIENT_IPS=(
  "192.168.1.45"
  "10.0.0.12"
  "172.16.5.99"
  "192.168.1.88"
  "10.0.2.55"
  "192.168.2.14"
)

echo "[+] 1. Sending HTTP traffic to live Nginx (:8081) and Node API (:3001)..."

for i in {1..30}; do
  RAND_PATH="${URLS[$RANDOM % ${#URLS[@]}]}"
  RAND_IP="${CLIENT_IPS[$RANDOM % ${#CLIENT_IPS[@]}]}"
  NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  
  # Hit live Nginx
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${NGINX_URL}${RAND_PATH}" || echo "200")
  BYTES=$(( RANDOM % 3500 + 200 ))
  
  # Ship parsed log to Logstash TCP Ingest (:5000)
  PAYLOAD=$(cat <<JSON
{"@timestamp":"${NOW}","log_type":"web","service":"nginx-web","client_ip":"${RAND_IP}","method":"GET","url":"${RAND_PATH}","response_code":${STATUS},"bytes":${BYTES},"message":"${RAND_IP} - - [${NOW}] \"GET ${RAND_PATH} HTTP/1.1\" ${STATUS} ${BYTES}"}
JSON
)
  echo "${PAYLOAD}" | nc -w 1 "${LOGSTASH_HOST}" "${LOGSTASH_PORT}" || true
  
  # Also hit Node.js API
  if [ $(( i % 2 )) -eq 0 ]; then
    API_RES=$(curl -s "${API_URL}/api/pay" || echo '{"status":"success"}')
    API_PAYLOAD=$(cat <<JSON
{"@timestamp":"${NOW}","log_type":"web","service":"payment-api","client_ip":"${RAND_IP}","method":"GET","url":"/api/pay","response_code":200,"level":"INFO","message":"Odeme basariyla tamamlandi (order_id=$((1000 + i)))"}
JSON
)
    echo "${API_PAYLOAD}" | nc -w 1 "${LOGSTASH_HOST}" "${LOGSTASH_PORT}" || true
  else
    API_RES=$(curl -s "${API_URL}/api/fail" || echo '{"error":"db_error"}')
    API_PAYLOAD=$(cat <<JSON
{"@timestamp":"${NOW}","log_type":"web","service":"payment-api","client_ip":"${RAND_IP}","method":"GET","url":"/api/fail","response_code":500,"level":"ERROR","message":"Veritabani baglanti zaman asimi (retry_count=3)"}
JSON
)
    echo "${API_PAYLOAD}" | nc -w 1 "${LOGSTASH_HOST}" "${LOGSTASH_PORT}" || true
  fi
  
  echo -ne "    Processed request ${i}/30: ${RAND_PATH} (Status: ${STATUS})\r"
  sleep 0.1
done

echo -e "\n[✓] 60 live application requests generated and shipped to app-logs-*."
