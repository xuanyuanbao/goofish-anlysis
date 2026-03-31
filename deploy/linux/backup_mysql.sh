#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
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
APP_DB_USER="${XY_MYSQL_USER:-xianyu}"
APP_DB_PASSWORD="${XY_MYSQL_PASSWORD:-xianyu123456}"
APP_DB_NAME="${XY_MYSQL_DATABASE:-xianyu_report}"
BACKUP_DIR="${BACKUP_DIR:-${ROOT_DIR}/backup/mysql}"
TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
BACKUP_FILE="${BACKUP_DIR}/xianyu_report_${TIMESTAMP}.sql"

mkdir -p "${BACKUP_DIR}"

docker exec "${MYSQL_CONTAINER_NAME}" sh -c \
  "mysqldump -u\"${APP_DB_USER}\" -p\"${APP_DB_PASSWORD}\" --single-transaction --quick --set-gtid-purged=OFF \"${APP_DB_NAME}\"" \
  > "${BACKUP_FILE}"

gzip -f "${BACKUP_FILE}"

echo "[INFO] MySQL backup created: ${BACKUP_FILE}.gz"
