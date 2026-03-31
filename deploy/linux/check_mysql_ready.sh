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
APP_DB_USER="${XY_MYSQL_USER:-xianyu}"
APP_DB_PASSWORD="${XY_MYSQL_PASSWORD:-xianyu123456}"
APP_DB_NAME="${XY_MYSQL_DATABASE:-${MYSQL_DATABASE}}"

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

for REQUIRED_TABLE in keyword_config item_snapshot keyword_daily_stats item_score_daily job_run_history keyword_failure_log data_quality_issue; do
  if ! grep -qx "${REQUIRED_TABLE}" <<< "${TABLES_OUTPUT}"; then
    echo "[ERROR] Required table is missing: ${REQUIRED_TABLE}"
    exit 1
  fi
done

docker exec "${MYSQL_CONTAINER_NAME}" \
  mysql -h127.0.0.1 -u"${APP_DB_USER}" -p"${APP_DB_PASSWORD}" -D "${APP_DB_NAME}" \
  -e "SELECT 1;" >/dev/null

echo "[INFO] Docker is running."
echo "[INFO] MySQL container is healthy: ${MYSQL_CONTAINER_NAME}"
echo "[INFO] Database schema is ready: ${MYSQL_DATABASE}"
echo "[INFO] Application user login is valid: ${APP_DB_USER}"

if [[ "${XY_DB_BACKEND:-mysql}" != "mysql" ]]; then
  echo "[WARN] XY_DB_BACKEND is not mysql in app.env."
fi

echo "[INFO] Validation finished successfully."
