#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/mysql.env"
SQL_FILE="${SCRIPT_DIR}/mysql_bootstrap.sql"

if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${SCRIPT_DIR}/mysql.env.example" "${ENV_FILE}"
  echo "[INFO] mysql.env was not found. A default file has been created at ${ENV_FILE}."
fi

set -a
source "${ENV_FILE}"
set +a

MYSQL_CONTAINER_NAME="${MYSQL_CONTAINER_NAME:-xianyu-mysql}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-root123456}"

if ! docker ps --format '{{.Names}}' | grep -qx "${MYSQL_CONTAINER_NAME}"; then
  echo "[ERROR] MySQL container is not running: ${MYSQL_CONTAINER_NAME}"
  exit 1
fi

docker exec -i "${MYSQL_CONTAINER_NAME}" mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" < "${SQL_FILE}"

echo "[INFO] Bootstrap SQL executed successfully."
echo "[INFO] Default database: xianyu_report"
echo "[INFO] Default application user: xianyu"
