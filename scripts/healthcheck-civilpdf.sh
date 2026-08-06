#!/usr/bin/env bash
#
# CivilPDF-DX — production health check.
# Verifies local backend/frontend and the public Cloudflare Tunnel URL.
# Exit code 0 = healthy. Non-zero = degraded/down.
#
# Usage:
#   ./scripts/healthcheck-civilpdf.sh
#   ./scripts/healthcheck-civilpdf.sh --quiet
#
set -uo pipefail

QUIET=0
[[ "${1:-}" == "--quiet" ]] && QUIET=1

BACKEND_URL="${CIVILPDF_BACKEND_URL:-http://127.0.0.1:8180}"
FRONTEND_URL="${CIVILPDF_FRONTEND_URL:-http://127.0.0.1:5182}"
PUBLIC_URL="${CIVILPDF_PUBLIC_URL:-https://civilpdf.mirai-dx-platform.com/}"

FAIL=0

check() {
  local name="$1" url="$2" expect="$3"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "$url" 2>/dev/null)"
  if [[ "$code" == "$expect" ]]; then
    [[ $QUIET -eq 0 ]] && echo "OK   $name ($code)"
  else
    echo "FAIL $name (expected $expect, got ${code:-timeout})" >&2
    FAIL=1
  fi
}

check "backend /health"      "$BACKEND_URL/health" 200
check "frontend /"           "$FRONTEND_URL/" 200
check "public HTTPS"         "$PUBLIC_URL" 200
check "public API auth gate" "${PUBLIC_URL}api/v1/stats/" 401

if [[ $FAIL -ne 0 ]]; then
  echo "HEALTHCHECK: DEGRADED" >&2
  exit 1
fi
[[ $QUIET -eq 0 ]] && echo "HEALTHCHECK: OK"
exit 0
