#!/usr/bin/env bash
#
# CivilPDF-DX — production health check.
# Verifies local backend/frontend, the public Cloudflare Tunnel URL, database
# readiness, and backup freshness.
# Exit code 0 = healthy. Non-zero = degraded/down.
#
# Usage:
#   ./scripts/healthcheck-civilpdf.sh
#   ./scripts/healthcheck-civilpdf.sh --quiet
#
# Environment:
#   CIVILPDF_BACKEND_URL            default http://127.0.0.1:8180
#   CIVILPDF_FRONTEND_URL           default http://127.0.0.1:5182
#   CIVILPDF_PUBLIC_URL             default https://civilpdf.mirai-dx-platform.com/
#   BACKUP_ROOT                     default $HOME/civildx-backups
#   CIVILPDF_BACKUP_MAX_AGE_HOURS   default 36 (daily backup + slack)
#   CIVILPDF_SKIP_BACKUP_CHECK      set to 1 to skip the backup freshness check
#
# Why database readiness and backup freshness are checked here: on 2026-08-29
# the production PostgreSQL credential stopped authenticating. /health only
# reported that the process was alive, so every database-backed request returned
# HTTP 500 for three weeks while this check stayed green, and the daily backup
# silently produced 0-byte dumps the whole time. Both failures are now visible.
#
set -uo pipefail

QUIET=0
[[ "${1:-}" == "--quiet" ]] && QUIET=1

BACKEND_URL="${CIVILPDF_BACKEND_URL:-http://127.0.0.1:8180}"
FRONTEND_URL="${CIVILPDF_FRONTEND_URL:-http://127.0.0.1:5182}"
PUBLIC_URL="${CIVILPDF_PUBLIC_URL:-https://civilpdf.mirai-dx-platform.com/}"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/civildx-backups}"
BACKUP_MAX_AGE_HOURS="${CIVILPDF_BACKUP_MAX_AGE_HOURS:-36}"
SKIP_BACKUP_CHECK="${CIVILPDF_SKIP_BACKUP_CHECK:-0}"

FAIL=0

fail() {
  echo "FAIL $*" >&2
  FAIL=1
}

check() {
  local name="$1" url="$2" expect="$3"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "$url" 2>/dev/null)"
  if [[ "$code" == "$expect" ]]; then
    [[ $QUIET -eq 0 ]] && echo "OK   $name ($code)"
  else
    fail "$name (expected $expect, got ${code:-timeout})"
  fi
}

# --- service endpoints -----------------------------------------------------
check "backend /health"       "$BACKEND_URL/health" 200
check "backend /health/ready" "$BACKEND_URL/health/ready" 200
check "frontend /"            "$FRONTEND_URL/" 200
check "public HTTPS"          "$PUBLIC_URL" 200
check "public API auth gate"  "${PUBLIC_URL}api/v1/stats/" 401

# --- backup freshness ------------------------------------------------------
# A backup only counts as a usable recovery point when its dump/database file
# exists and is non-empty: an aborted pg_dump leaves a 0-byte file behind.
newest_epoch=0
newest_dir=""

if [[ "$SKIP_BACKUP_CHECK" == "1" ]]; then
  [[ $QUIET -eq 0 ]] && echo "SKIP backup freshness (CIVILPDF_SKIP_BACKUP_CHECK=1)"
elif [[ ! -d "$BACKUP_ROOT" ]]; then
  [[ $QUIET -eq 0 ]] && echo "WARN backup root not found: $BACKUP_ROOT"
else
  while IFS= read -r dir; do
    for candidate in "$dir/civilpdf.dump" "$dir/civilpdf_dev.db"; do
      if [[ -s "$candidate" ]]; then
        epoch="$(stat -c %Y "$dir" 2>/dev/null || echo 0)"
        if ((epoch > newest_epoch)); then
          newest_epoch="$epoch"
          newest_dir="$dir"
        fi
        break
      fi
    done
  done < <(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d 2>/dev/null)

  if ((newest_epoch == 0)); then
    fail "backup freshness (no non-empty backup found under $BACKUP_ROOT)"
  else
    now_epoch="$(date +%s)"
    age_hours=$(((now_epoch - newest_epoch) / 3600))
    if ((age_hours > BACKUP_MAX_AGE_HOURS)); then
      fail "backup freshness (newest valid backup is ${age_hours}h old, limit ${BACKUP_MAX_AGE_HOURS}h): $newest_dir"
    else
      [[ $QUIET -eq 0 ]] && echo "OK   backup freshness (${age_hours}h old: $newest_dir)"
    fi
  fi
fi

if [[ $FAIL -ne 0 ]]; then
  echo "HEALTHCHECK: DEGRADED" >&2
  exit 1
fi
[[ $QUIET -eq 0 ]] && echo "HEALTHCHECK: OK"
exit 0
