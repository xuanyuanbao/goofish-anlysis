#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MYSQL_ENV_FILE="${SCRIPT_DIR}/mysql.env"
APP_ENV_FILE="${SCRIPT_DIR}/app.env"

if [[ -f "${MYSQL_ENV_FILE}" ]]; then
  set -a
  source "${MYSQL_ENV_FILE}"
  set +a
fi

if [[ -f "${APP_ENV_FILE}" ]]; then
  set -a
  source "${APP_ENV_FILE}"
  set +a
fi

MYSQL_CONTAINER_NAME="${MYSQL_CONTAINER_NAME:-xianyu-mysql}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-root123456}"
MYSQL_DATABASE="${MYSQL_DATABASE:-xianyu_report}"

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] Docker is not installed."
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "${MYSQL_CONTAINER_NAME}"; then
  echo "[ERROR] MySQL container is not running: ${MYSQL_CONTAINER_NAME}"
  exit 1
fi

docker exec "${MYSQL_CONTAINER_NAME}" mysqladmin ping -uroot -p"${MYSQL_ROOT_PASSWORD}" --silent >/dev/null

TABLES_OUTPUT="$(docker exec "${MYSQL_CONTAINER_NAME}" mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" -Nse "USE ${MYSQL_DATABASE}; SHOW TABLES;")"

for REQUIRED_TABLE in keyword_config item_snapshot keyword_daily_stats item_score_daily; do
  if ! grep -qx "${REQUIRED_TABLE}" <<< "${TABLES_OUTPUT}"; then
    echo "[ERROR] Required table is missing: ${REQUIRED_TABLE}"
    exit 1
  fi
done

echo "[INFO] Docker is running."
echo "[INFO] MySQL container is healthy: ${MYSQL_CONTAINER_NAME}"
echo "[INFO] Database schema is ready: ${MYSQL_DATABASE}"

if [[ "${XY_DB_BACKEND:-mysql}" != "mysql" ]]; then
  echo "[WARN] XY_DB_BACKEND is not mysql in app.env."
fi

echo "[INFO] Validation finished successfully."
