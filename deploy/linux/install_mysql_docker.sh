#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${SCRIPT_DIR}/mysql.env"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.mysql.yml"
MYSQL_DATA_DIR_DEFAULT="${SCRIPT_DIR}/mysql-data"

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] Docker is not installed. Run deploy/linux/install_docker.sh first."
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${SCRIPT_DIR}/mysql.env.example" "${ENV_FILE}"
  echo "[INFO] mysql.env was not found. A default file has been created at ${ENV_FILE}."
fi

set -a
source "${ENV_FILE}"
set +a

mkdir -p "${MYSQL_DATA_DIR:-${MYSQL_DATA_DIR_DEFAULT}}"

if docker compose version >/dev/null 2>&1; then
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d
elif command -v docker-compose >/dev/null 2>&1; then
  docker-compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d
else
  echo "[ERROR] docker compose is not available."
  exit 1
fi

echo "[INFO] MySQL container started."
echo "[INFO] Root directory: ${ROOT_DIR}"
echo "[INFO] Data directory: ${MYSQL_DATA_DIR:-${MYSQL_DATA_DIR_DEFAULT}}"
