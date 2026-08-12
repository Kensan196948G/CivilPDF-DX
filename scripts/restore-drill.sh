#!/usr/bin/env bash
#
# CivilPDF-DX — backup restore drill (non-destructive)
#
# Restores the latest production backup into a temporary directory, starts a
# backend instance against the restored copy, and verifies:
#   1. SQLite integrity + alembic version == head
#   2. uploads file count matches the backup
#   3. /health responds
#   4. login -> /auth/me -> /projects work on the restored data
#
# The production data is NEVER touched. On failure an alert email is sent.
#
# Usage:
#   ./scripts/restore-drill.sh                      # latest backup, port 8199
#   ./scripts/restore-drill.sh --backup ~/civildx-backups/<stamp>
#   ./scripts/restore-drill.sh --port 8299 --keep   # keep temp dir for debugging
#
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/src/console/backend"
BACKUP_ROOT="${CIVILPDF_BACKUP_ROOT:-$HOME/civildx-backups}"
PORT="${CIVILPDF_DRILL_PORT:-8199}"
KEEP=0
LOGFILE="${CIVILPDF_DRILL_LOG:-$HOME/.local/state/civildx-drill/drill.log}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backup) BACKUP_DIR="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --keep) KEEP=1; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

if [[ ! "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 1024 || PORT > 65535 )); then
  echo "ERROR: invalid port: $PORT" >&2
  exit 2
fi

mkdir -p "$(dirname "$LOGFILE")"
log() { printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" | tee -a "$LOGFILE"; }

# --- locate backup -----------------------------------------------------------
if [[ -z "${BACKUP_DIR:-}" ]]; then
  BACKUP_DIR="$(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name '[0-9]*' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)"
fi
if [[ -z "${BACKUP_DIR:-}" || ! -f "$BACKUP_DIR/civilpdf_dev.db" ]]; then
  log "ERROR: no valid backup found under $BACKUP_ROOT"
  exit 2
fi
log "drill start: backup=$BACKUP_DIR port=$PORT"

WORK="$(mktemp -d /tmp/civildx-restore-drill.XXXXXX)"
cp "$BACKUP_DIR/civilpdf_dev.db" "$WORK/restored.db"
mkdir -p "$WORK/uploads"
if [[ -d "$BACKUP_DIR/uploads" ]]; then
  cp -a "$BACKUP_DIR/uploads"/. "$WORK/uploads/"
fi

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  if [[ $KEEP -eq 0 ]]; then
    rm -rf "$WORK"
  else
    log "kept workdir: $WORK"
  fi
}
trap cleanup EXIT

FAIL=0
fail() { log "FAIL: $*"; FAIL=1; }

# --- 1. integrity + alembic version ------------------------------------------
python3 - "$WORK/restored.db" <<'PY'
import sqlite3, sys

con = sqlite3.connect(sys.argv[1])
rows = con.execute("PRAGMA integrity_check").fetchall()
con.close()
assert rows == [("ok",)], f"integrity check failed: {rows}"
PY
log "OK  restored DB integrity"

# Production boot runs `alembic upgrade head` (systemd ExecStartPre) — replicate
# it on the restored copy so pre-migration backups are also validated.
if ! (
  cd "$BACKEND_DIR"
  DATABASE_URL="sqlite:///$WORK/restored.db" PYTHONPATH=. alembic upgrade head >/dev/null 2>&1
); then
  fail "alembic upgrade head on restored copy failed"
fi

DB_VERSION="$(python3 - "$WORK/restored.db" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
row = con.execute("select version_num from alembic_version").fetchone()
print(row[0] if row else "MISSING")
con.close()
PY
)"
HEAD_VERSION="$(cd "$BACKEND_DIR" && alembic heads 2>/dev/null | awk '{print $1}' | head -1)"
if [[ "$DB_VERSION" == "$HEAD_VERSION" ]]; then
  log "OK  alembic upgrade head on restored copy -> $DB_VERSION"
else
  fail "alembic version after upgrade mismatch: db=$DB_VERSION head=$HEAD_VERSION"
fi

# --- 2. uploads count ----------------------------------------------------------
BACKUP_COUNT="$(find "$BACKUP_DIR/uploads" -type f 2>/dev/null | wc -l)"
RESTORED_COUNT="$(find "$WORK/uploads" -type f 2>/dev/null | wc -l)"
if [[ "$BACKUP_COUNT" == "$RESTORED_COUNT" ]]; then
  log "OK  uploads files restored ($RESTORED_COUNT)"
else
  fail "uploads count mismatch: backup=$BACKUP_COUNT restored=$RESTORED_COUNT"
fi

# --- 3. start restored backend ------------------------------------------------
python3 - "$PORT" "$WORK" "$BACKEND_DIR" <<'PY' >"$WORK/uvicorn.log" 2>&1 &
import os, sys
from dotenv import dotenv_values

port, work, backend_dir = sys.argv[1], sys.argv[2], sys.argv[3]
os.chdir(backend_dir)
vals = dotenv_values(os.path.expanduser("~/.config/civilpdf/civilpdf.env"))
for k, v in vals.items():
    if v is not None:
        os.environ.setdefault(k, v)
os.environ["DATABASE_URL"] = f"sqlite:///{work}/restored.db"
os.environ["DEBUG"] = "false"
from uvicorn import run
run("main:app", host="127.0.0.1", port=int(port))
PY
SERVER_PID=$!

for _ in $(seq 1 30); do
  if curl -sS -o /dev/null --max-time 2 "http://127.0.0.1:$PORT/health" 2>/dev/null; then
    break
  fi
  sleep 1
done
if curl -sS -o /dev/null --max-time 3 "http://127.0.0.1:$PORT/health"; then
  log "OK  restored backend /health on port $PORT"
else
  fail "restored backend did not become healthy (see $WORK/uvicorn.log)"
  tail -5 "$WORK/uvicorn.log" | tee -a "$LOGFILE"
fi

# --- 4. auth flow on restored data ---------------------------------------------
if [[ $FAIL -eq 0 ]]; then
  python3 - "$WORK/restored.db" <<'PY'
import bcrypt, sqlite3, sys

con = sqlite3.connect(sys.argv[1])
hashed = bcrypt.hashpw(b"DrillPass123!", bcrypt.gensalt()).decode()
con.execute(
    "insert or replace into users "
    "(id,email,username,full_name,hashed_password,role,status,created_at) "
    "values (?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
    ("drill-user-0001", "drill@civildx.local", "drill", "Restore Drill",
     hashed, "ENGINEER", "ACTIVE"),
)
con.commit()
con.close()
PY
  TOKEN="$(curl -sS -X POST "http://127.0.0.1:$PORT/api/v1/auth/token" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -d 'username=drill@civildx.local&password=DrillPass123!' \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])' 2>/dev/null || true)"
  if [[ -n "$TOKEN" ]]; then
    ME="$(curl -sS "http://127.0.0.1:$PORT/api/v1/auth/me" -H "Authorization: Bearer $TOKEN" 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["email"], d["role"])' 2>/dev/null || true)"
    PROJECTS_CODE="$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/api/v1/projects/" -H "Authorization: Bearer $TOKEN" 2>/dev/null)"
    if [[ "$ME" == "drill@civildx.local engineer" && "$PROJECTS_CODE" == "200" ]]; then
      log "OK  auth flow on restored data (me=$ME projects=$PROJECTS_CODE)"
    else
      fail "auth flow mismatch: me='$ME' projects=$PROJECTS_CODE"
    fi
  else
    fail "login on restored data failed"
  fi
fi

# --- summary --------------------------------------------------------------------
if [[ $FAIL -eq 0 ]]; then
  log "DRILL PASS — backup restore verified: $BACKUP_DIR"
  exit 0
else
  "$PROJECT_DIR/scripts/alert-notify.sh" \
    "[CivilPDF-DX] バックアップ復元訓練 失敗" \
    "復元訓練で検証に失敗しました。
backup: $BACKUP_DIR
log:    $LOGFILE
詳細:   tail -50 $LOGFILE" || true
  log "DRILL FAIL — see $LOGFILE"
  exit 1
fi
