#!/usr/bin/env bash
set -euo pipefail

BEGIN_MARK="# BEGIN GOOFISH_ANALYSIS_DOCKER"
END_MARK="# END GOOFISH_ANALYSIS_DOCKER"
LEGACY_BEGIN_MARK="# BEGIN GOOFISH_ANALYSIS"
LEGACY_END_MARK="# END GOOFISH_ANALYSIS"
TMP_CRON="$(mktemp)"

(crontab -l 2>/dev/null || true)   | sed "/^${LEGACY_BEGIN_MARK}$/,/^${LEGACY_END_MARK}$/d"   | sed "/^${BEGIN_MARK}$/,/^${END_MARK}$/d"   > "${TMP_CRON}"
crontab "${TMP_CRON}"
rm -f "${TMP_CRON}"

echo "[INFO] Cron jobs removed successfully."
