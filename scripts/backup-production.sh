#!/usr/bin/env bash
#
# CivilPDF-DX — production backup (PostgreSQL/Neon or SQLite DB + uploads + env)
#
# Creates a timestamped snapshot under BACKUP_ROOT (default ~/civildx-backups)
# and prunes snapshots older than RETENTION_DAYS (default 14).
#
# Usage:
#   ./scripts/backup-production.sh            # full backup + prune
#   BACKUP_ROOT=/mnt/backup ./scripts/backup-production.sh
#
# Restore:
#   1. systemctl --user stop civilpdf-backend.service
#   2a. SQLite: cp <BACKUP_ROOT>/<stamp>/civilpdf_dev.db <repo>/src/console/backend/
#   2b. PostgreSQL: pg_restore --clean --if-exists --dbname "$DATABASE_URL" \
#          <BACKUP_ROOT>/<stamp>/civilpdf.dump
#   3. rm -rf ~/civildx/uploads && cp -a <BACKUP_ROOT>/<stamp>/uploads/. ~/civildx/uploads/
#   4. systemctl --user start civilpdf-backend.service
#
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${CIVILPDF_DB_PATH:-$PROJECT_DIR/src/console/backend/civilpdf_dev.db}"
UPLOAD_DIR="${CIVILPDF_UPLOAD_DIR:-$HOME/civildx/uploads}"
ENV_FILE="${CIVILPDF_ENV_FILE:-$HOME/.config/civilpdf/civilpdf.env}"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/civildx-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

if [[ ! "$RETENTION_DAYS" =~ ^[0-9]+$ ]]; then
  echo "ERROR: RETENTION_DAYS must be a non-negative integer (got '$RETENTION_DAYS')" >&2
  exit 1
fi
if [[ "$BACKUP_ROOT" == "/" || "$BACKUP_ROOT" == "$HOME" ]]; then
  echo "ERROR: refusing to use '$BACKUP_ROOT' as BACKUP_ROOT (too broad for pruning)" >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="$BACKUP_ROOT/$STAMP"

mkdir -p "$DEST/uploads"

# 本番 env から DATABASE_URL を読み込み、PostgreSQL か SQLite かを判定する
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ "${DATABASE_URL:-}" == postgres* ]]; then
  # サーバー major に一致する pg_dump を優先（バージョン不整合を回避）
  PG_BIN=""
  for d in /usr/lib/postgresql/*/bin; do
    if [[ -x "$d/pg_dump" ]]; then PG_BIN="$d"; fi
  done
  if [[ -z "$PG_BIN" ]] && command -v pg_dump >/dev/null 2>&1; then
    PG_BIN="$(dirname "$(command -v pg_dump)")"
  fi
  if [[ -z "$PG_BIN" ]]; then
    echo "ERROR: pg_dump がインストールされていません" >&2
    exit 1
  fi
  PG_DUMP="$PG_BIN/pg_dump"
  PG_RESTORE="$PG_BIN/pg_restore"
  echo "PostgreSQL backup: $PG_DUMP -> $DEST/civilpdf.dump"
  "$PG_DUMP" "$DATABASE_URL" --format=custom --file="$DEST/civilpdf.dump"
  "$PG_RESTORE" --list "$DEST/civilpdf.dump" >/dev/null
  echo "PostgreSQL dump verified"
elif [[ -f "$DB_PATH" ]]; then
  echo "SQLite backup: online backup -> $DEST/civilpdf_dev.db"
  python3 - "$DB_PATH" "$DEST/civilpdf_dev.db" <<'PY'
import sqlite3
import sys

src, dst = sys.argv[1], sys.argv[2]
con = sqlite3.connect(src)
backup = sqlite3.connect(dst)
with backup:
    con.backup(backup)
backup.close()
con.close()
print(f"DB backup ok: {dst}")
PY
  python3 - "$DEST/civilpdf_dev.db" <<'PY'
import sqlite3
import sys

con = sqlite3.connect(sys.argv[1])
rows = con.execute("PRAGMA integrity_check").fetchall()
con.close()
assert rows == [("ok",)], f"integrity check failed: {rows}"
print("DB integrity ok")
PY
else
  echo "ERROR: DB not found (DATABASE_URL 未設定かつ $DB_PATH なし)" >&2
  exit 1
fi

# アップロード済みファイル（構造を保持してコピー）
cp -a "$UPLOAD_DIR"/. "$DEST/uploads/"

# 環境設定（シークレットを含むため root 以外読めない権限で保持）
if [[ -f "$ENV_FILE" ]]; then
  cp -a "$ENV_FILE" "$DEST/civilpdf.env"
  chmod 600 "$DEST/civilpdf.env"
fi

# 保持期間より古いバックアップを削除
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +"$RETENTION_DAYS" \
  -exec rm -rf {} +

echo "Backup complete: $DEST"
