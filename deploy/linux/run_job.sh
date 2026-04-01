#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
IMAGE_NAME="${IMAGE_NAME:-goofish-analysis:latest}"
DOCKER_BIN="${DOCKER_BIN:-/usr/bin/docker}"
APP_ENV_FILE="${APP_ENV_FILE:-${SCRIPT_DIR}/app.env}"

if [[ ! -f "${APP_ENV_FILE}" ]]; then
  echo "[ERROR] Missing env file: ${APP_ENV_FILE}" >&2
  exit 1
fi

cd "${ROOT_DIR}"
mkdir -p "${ROOT_DIR}/data" "${ROOT_DIR}/reports" "${ROOT_DIR}/logs"

exec "${DOCKER_BIN}" run   --rm   --network host   --env-file "${APP_ENV_FILE}"   -v "${ROOT_DIR}/data:/app/data"   -v "${ROOT_DIR}/reports:/app/reports"   -v "${ROOT_DIR}/logs:/app/logs"   "${IMAGE_NAME}"   "$@"
