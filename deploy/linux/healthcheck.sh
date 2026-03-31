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

IMAGE_NAME="${IMAGE_NAME:-goofish-analysis:latest}"
MYSQL_CONTAINER_NAME="${MYSQL_CONTAINER_NAME:-xianyu-mysql}"
APP_DB_USER="${XY_MYSQL_USER:-xianyu}"
APP_DB_PASSWORD="${XY_MYSQL_PASSWORD:-xianyu123456}"
APP_DB_NAME="${XY_MYSQL_DATABASE:-xianyu_report}"

cd "${ROOT_DIR}"

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] docker command is not available."
  exit 1
fi

if ! docker image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
  echo "[ERROR] Docker image is missing: ${IMAGE_NAME}"
  exit 1
fi

bash "${SCRIPT_DIR}/check_mysql_ready.sh"

LATEST_RUN="$(docker exec "${MYSQL_CONTAINER_NAME}" mysql -Nse \
  "SELECT CONCAT_WS('|', run_id, job_name, run_status, COALESCE(alert_level,''), DATE_FORMAT(finished_at, '%Y-%m-%d %H:%i:%s')) FROM ${APP_DB_NAME}.job_run_history ORDER BY finished_at DESC LIMIT 1;" \
  -u"${APP_DB_USER}" -p"${APP_DB_PASSWORD}" 2>/dev/null || true)"

if [[ -z "${LATEST_RUN}" ]]; then
  echo "[WARN] No rows found in job_run_history yet."
else
  IFS='|' read -r LATEST_RUN_ID LATEST_JOB_NAME LATEST_RUN_STATUS LATEST_ALERT_LEVEL LATEST_FINISHED_AT <<< "${LATEST_RUN}"
  echo "[INFO] Latest run: id=${LATEST_RUN_ID} job=${LATEST_JOB_NAME} status=${LATEST_RUN_STATUS} alert=${LATEST_ALERT_LEVEL} finished_at=${LATEST_FINISHED_AT}"
  if [[ "${LATEST_RUN_STATUS}" != "success" ]]; then
    echo "[ERROR] Latest job run is not successful."
    exit 1
  fi
fi

docker run --rm --network host --env-file "${APP_ENV_FILE}" "${IMAGE_NAME}" --help >/dev/null

echo "[INFO] Healthcheck finished successfully."
