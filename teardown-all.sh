#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[+] Stopping and removing demo microservice apps..."
docker compose -f "${SCRIPT_DIR}/02-workspace-apps-logging/sample-apps/docker-compose.apps.yml" down -v --remove-orphans || true

echo "[+] Stopping and removing Docker container log harvester (if running)..."
docker compose -f "${SCRIPT_DIR}/03-docker-container-logs/docker-compose.filebeat.yml" down -v --remove-orphans 2>/dev/null || true
docker rm -f filebeat-linux 2>/dev/null || true

echo "[+] Removing Kubernetes logging DaemonSet and test workloads (if deployed)..."
if command -v kubectl >/dev/null 2>&1; then
  kubectl delete -f "${SCRIPT_DIR}/04-kubernetes-cluster-logs/multiline-app-deployment.yaml" --ignore-not-found=true 2>/dev/null || true
  kubectl delete -f "${SCRIPT_DIR}/04-kubernetes-cluster-logs/filebeat-kubernetes-daemonset.yaml" --ignore-not-found=true 2>/dev/null || true
fi

echo "[+] Stopping and removing core ELK stack..."
docker compose -f "${SCRIPT_DIR}/00-elk-core-stack/docker-compose.yml" down -v --remove-orphans || true

echo "[✓] All ELK lab containers, pipelines and volumes have been cleaned up."
echo "[✓] Kubernetes cluster and other workspace services were preserved."
