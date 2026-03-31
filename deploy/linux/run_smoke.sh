#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
IMAGE_NAME="${IMAGE_NAME:-goofish-analysis:latest}"

mkdir -p "${ROOT_DIR}/data" "${ROOT_DIR}/reports" "${ROOT_DIR}/logs"

cd "${ROOT_DIR}"
/usr/bin/docker run --rm \
  --network host \
  -e XY_DB_BACKEND=sqlite \
  -e XY_DB_PATH=/app/data/smoke_test.db \
  -e XY_CRAWLER_MODE=fixture \
  -e XY_ALLOW_FIXTURE_WRITE=1 \
  -v "${ROOT_DIR}/data:/app/data" \
  -v "${ROOT_DIR}/reports:/app/reports" \
  -v "${ROOT_DIR}/logs:/app/logs" \
  "${IMAGE_NAME}" \
  "$@"
