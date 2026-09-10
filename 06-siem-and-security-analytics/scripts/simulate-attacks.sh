#!/usr/bin/env bash
set -euo pipefail

LOGSTASH_HOST="${LOGSTASH_HOST:-127.0.0.1}"
LOGSTASH_TCP_PORT="${LOGSTASH_TCP_PORT:-5000}"
NGINX_URL="${NGINX_URL:-http://localhost:8081}"

echo "[+] 1. Simulating SSH Brute Force Attack via Logstash TCP Ingestion (:5000)..."
ATTACKER_IP="198.51.100.77"
TARGET_USERS=("root" "admin" "ubuntu" "deploy" "test" "oracle")

for user in "${TARGET_USERS[@]}"; do
  NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  PAYLOAD=$(cat <<JSON
{"@timestamp":"${NOW}","log_type":"auth","message":"Failed password for invalid user ${user} from ${ATTACKER_IP} port 49822 ssh2","client_ip":"${ATTACKER_IP}","user":"${user}","event":{"action":"ssh_login","outcome":"failure"}}
JSON
)
  echo "${PAYLOAD}" | nc -w 1 "${LOGSTASH_HOST}" "${LOGSTASH_TCP_PORT}" || true
  echo "    Sent SSH failed login for user: ${user} from ${ATTACKER_IP}"
  sleep 0.3
done

echo "[+] 2. Simulating Web Attacks against Nginx Application (${NGINX_URL})..."
MALICIOUS_PATHS=(
  "/../../../../etc/passwd"
  "/.git/config"
  "/.env"
  "/wp-login.php"
  "/api/v1/users?id=1%20UNION%20SELECT%20username,password%20FROM%20users"
  "/cgi-bin/test.cgi"
  "/admin/config.php"
)

for path in "${MALICIOUS_PATHS[@]}"; do
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${NGINX_URL}${path}" || echo "000")
  echo "    Requested ${NGINX_URL}${path} -> Status: ${HTTP_STATUS}"
  sleep 0.3
done

echo "[✓] Attack simulation completed. Check Kibana Discover / SIEM alerts."
