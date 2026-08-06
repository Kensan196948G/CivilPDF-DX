#!/usr/bin/env bash
#
# CivilPDF-DX — production backup (SQLite DB + uploaded files + env config)
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
#   2. cp <BACKUP_ROOT>/<stamp>/civilpdf_dev.db <repo>/src/console/backend/
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

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="$BACKUP_ROOT/$STAMP"

if [[ ! -f "$DB_PATH" ]]; then
  echo "ERROR: DB not found at $DB_PATH" >&2
  exit 1
fi

mkdir -p "$DEST/uploads"

# SQLite の安全なバックアップ: online backup API で一貫性を確保
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

# アップロード済みファイル（構造を保持してコピー）
cp -a "$UPLOAD_DIR"/. "$DEST/uploads/"

# 環境設定（シークレットを含むため root 以外読めない権限で保持）
if [[ -f "$ENV_FILE" ]]; then
  cp -a "$ENV_FILE" "$DEST/civilpdf.env"
  chmod 600 "$DEST/civilpdf.env"
fi

# 検証: DB が開けて整合性チェックに通ること
python3 - "$DEST/civilpdf_dev.db" <<'PY'
import sqlite3
import sys

con = sqlite3.connect(sys.argv[1])
rows = con.execute("PRAGMA integrity_check").fetchall()
con.close()
assert rows == [("ok",)], f"integrity check failed: {rows}"
print("DB integrity ok")
PY

# 保持期間より古いバックアップを削除
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +"$RETENTION_DAYS" \
  -exec rm -rf {} +

echo "Backup complete: $DEST"
