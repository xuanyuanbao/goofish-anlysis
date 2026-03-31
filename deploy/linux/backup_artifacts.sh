#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${ROOT_DIR}/backup/runtime}"
TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
ARCHIVE_FILE="${BACKUP_DIR}/goofish_runtime_${TIMESTAMP}.tar.gz"

mkdir -p "${BACKUP_DIR}"

cd "${ROOT_DIR}"
tar -czf "${ARCHIVE_FILE}" reports logs

echo "[INFO] Runtime artifact backup created: ${ARCHIVE_FILE}"
