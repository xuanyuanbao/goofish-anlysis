#!/usr/bin/env bash
set -euo pipefail

BEGIN_MARK="# BEGIN GOOFISH_ANALYSIS"
END_MARK="# END GOOFISH_ANALYSIS"
TMP_CRON="$(mktemp)"

(crontab -l 2>/dev/null || true) | sed "/^${BEGIN_MARK}$/,/^${END_MARK}$/d" > "${TMP_CRON}"
crontab "${TMP_CRON}"
rm -f "${TMP_CRON}"

echo "[INFO] Cron jobs removed successfully."
