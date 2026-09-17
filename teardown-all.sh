#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[+] Stopping and removing demo microservice apps..."
docker compose -f "${SCRIPT_DIR}/02-workspace-apps-logging/sample-apps/docker-compose.apps.yml" down -v --remove-orphans || true

echo "[+] Stopping and removing core ELK stack..."
docker compose -f "${SCRIPT_DIR}/00-elk-core-stack/docker-compose.yml" down -v --remove-orphans || true

echo "[✓] All lab containers and volumes have been cleaned up."
