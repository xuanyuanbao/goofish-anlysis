#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ -f "${SCRIPT_DIR}/app.env" ]]; then
  set -a
  source "${SCRIPT_DIR}/app.env"
  set +a
fi

cd "${ROOT_DIR}"
python3 main_weekly.py "$@"
