#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BEGIN_MARK="# BEGIN GOOFISH_ANALYSIS"
END_MARK="# END GOOFISH_ANALYSIS"
CRON_LOG_FILE="${ROOT_DIR}/logs/cron.log"
DEFAULT_CRAWL_LIMIT="${DEFAULT_CRAWL_LIMIT:-20}"

mkdir -p "${ROOT_DIR}/logs"
chmod +x \
  "${SCRIPT_DIR}/run_daily.sh" \
  "${SCRIPT_DIR}/run_weekly.sh" \
  "${SCRIPT_DIR}/run_monthly.sh"

TMP_CRON="$(mktemp)"
(crontab -l 2>/dev/null || true) | sed "/^${BEGIN_MARK}$/,/^${END_MARK}$/d" > "${TMP_CRON}"

cat >> "${TMP_CRON}" <<EOF
${BEGIN_MARK}
0 9 * * * cd "${ROOT_DIR}" && bash "${SCRIPT_DIR}/run_daily.sh" --mode crawl --limit ${DEFAULT_CRAWL_LIMIT} >> "${CRON_LOG_FILE}" 2>&1
0 13 * * * cd "${ROOT_DIR}" && bash "${SCRIPT_DIR}/run_daily.sh" --mode crawl --limit ${DEFAULT_CRAWL_LIMIT} >> "${CRON_LOG_FILE}" 2>&1
0 19 * * * cd "${ROOT_DIR}" && bash "${SCRIPT_DIR}/run_daily.sh" --mode crawl --limit ${DEFAULT_CRAWL_LIMIT} >> "${CRON_LOG_FILE}" 2>&1
0 23 * * * cd "${ROOT_DIR}" && bash "${SCRIPT_DIR}/run_daily.sh" --mode report >> "${CRON_LOG_FILE}" 2>&1
30 23 * * 1 cd "${ROOT_DIR}" && bash "${SCRIPT_DIR}/run_weekly.sh" >> "${CRON_LOG_FILE}" 2>&1
0 1 1 * * cd "${ROOT_DIR}" && bash "${SCRIPT_DIR}/run_monthly.sh" >> "${CRON_LOG_FILE}" 2>&1
${END_MARK}
EOF

crontab "${TMP_CRON}"
rm -f "${TMP_CRON}"

echo "[INFO] Cron jobs installed successfully."
echo "[INFO] Cron output file: ${CRON_LOG_FILE}"
