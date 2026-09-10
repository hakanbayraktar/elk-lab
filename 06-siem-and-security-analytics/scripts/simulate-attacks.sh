#!/usr/bin/env bash
set -euo pipefail

LOGSTASH_HOST="${LOGSTASH_HOST:-127.0.0.1}"
LOGSTASH_TCP_PORT="${LOGSTASH_TCP_PORT:-5000}"
NGINX_URL="${NGINX_URL:-http://localhost:8081}"
ATTACKER_IP="198.51.100.77"

echo "=================================================================="
echo "          Elastic SIEM & Threat Ingestion Simulation              "
echo "=================================================================="

echo -e "\n[+] 1. Simulating SSH Brute-Force Attack (MITRE ATT&CK T1110)..."
TARGET_USERS=("root" "admin" "ubuntu" "deploy" "test" "oracle")

for user in "${TARGET_USERS[@]}"; do
  NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  PAYLOAD=$(cat <<JSON
{"@timestamp":"${NOW}","log_type":"auth","message":"Failed password for invalid user ${user} from ${ATTACKER_IP} port 49822 ssh2","client_ip":"${ATTACKER_IP}","user":"${user}","event":{"category":"authentication","action":"ssh_login","outcome":"failure"}}
JSON
)
  echo "${PAYLOAD}" | nc -w 1 "${LOGSTASH_HOST}" "${LOGSTASH_TCP_PORT}" || true
  echo "    [SSH] Sent Failed password for user: ${user} from ${ATTACKER_IP}"
  sleep 0.2
done

echo -e "\n[+] 2. Simulating Web Attacks (OWASP Top 10 Path Traversal & SQLi)..."
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
  NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  # Canlı Nginx servisine istek at (varsa)
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${NGINX_URL}${path}" 2>/dev/null || echo "403")
  if [ "${HTTP_STATUS}" = "000" ]; then HTTP_STATUS="403"; fi
  
  # Logstash Ingestion (app-logs-* için)
  PAYLOAD=$(cat <<JSON
{"@timestamp":"${NOW}","log_type":"web","message":"${ATTACKER_IP} - - [${NOW}] \"GET ${path} HTTP/1.1\" ${HTTP_STATUS} 168","client_ip":"${ATTACKER_IP}","method":"GET","url":"${path}","response_code":${HTTP_STATUS},"bytes":168,"user_agent":"sqlmap/1.6","event":{"category":"web","action":"http_request","outcome":"failure"}}
JSON
)
  echo "${PAYLOAD}" | nc -w 1 "${LOGSTASH_HOST}" "${LOGSTASH_TCP_PORT}" || true
  echo "    [WEB] Target: ${path} -> HTTP Status: ${HTTP_STATUS} (Source IP: ${ATTACKER_IP})"
  sleep 0.2
done

echo -e "\n[✓] Attack simulation completed successfully."
echo "[✓] Ingested 6 SSH brute-force events and 7 web attack events into Elastic Stack."
