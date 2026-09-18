#!/usr/bin/env bash
#
# CivilPDF-DX — production backup (PostgreSQL/Neon or SQLite DB + uploads + env)
#
# Creates a timestamped snapshot under BACKUP_ROOT (default ~/civildx-backups)
# and prunes snapshots older than RETENTION_DAYS (default 14).
#
# The snapshot is assembled in a hidden ".incomplete-<stamp>" directory and only
# renamed into place after the dump has been verified. A failed run therefore
# leaves no directory behind: between 2026-08-29 and 2026-09-18 an invalid
# PostgreSQL credential made every run create a directory containing a 0-byte
# dump, which read as "a backup exists" in any directory listing and hid a
# three-week backup outage. Pruning also only runs after a verified success.
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
# Two runs inside the same second must not collide.
suffix=1
while [[ -e "$DEST" ]]; do
  DEST="$BACKUP_ROOT/$STAMP-$suffix"
  suffix=$((suffix + 1))
done
DEST_NAME="$(basename "$DEST")"
# Staging path: hidden, and clearly not a recovery point.
WORK="$BACKUP_ROOT/.incomplete-$DEST_NAME"
PUBLISHED=0

# On any failure, remove the staging directory so no partial snapshot survives.
cleanup_on_exit() {
  local rc=$?
  if ((rc != 0)) && [[ "$PUBLISHED" -eq 0 ]]; then
    echo "ERROR: backup failed (rc=$rc) — discarding incomplete snapshot" >&2
    rm -rf "$WORK"
  fi
  exit "$rc"
}
trap cleanup_on_exit EXIT

mkdir -p "$WORK/uploads"

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
  echo "PostgreSQL backup: $PG_DUMP -> $WORK/civilpdf.dump"
  "$PG_DUMP" "$DATABASE_URL" --format=custom --file="$WORK/civilpdf.dump"
  "$PG_RESTORE" --list "$WORK/civilpdf.dump" >/dev/null
  if [[ ! -s "$WORK/civilpdf.dump" ]]; then
    echo "ERROR: pg_dump produced an empty file" >&2
    exit 1
  fi
  echo "PostgreSQL dump verified ($(stat -c %s "$WORK/civilpdf.dump") bytes)"
elif [[ -f "$DB_PATH" ]]; then
  echo "SQLite backup: online backup -> $WORK/civilpdf_dev.db"
  python3 - "$DB_PATH" "$WORK/civilpdf_dev.db" <<'PY'
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
  python3 - "$WORK/civilpdf_dev.db" <<'PY'
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
if [[ -d "$UPLOAD_DIR" ]]; then
  cp -a "$UPLOAD_DIR"/. "$WORK/uploads/"
  echo "Uploads copied: $(find "$WORK/uploads" -type f | wc -l) file(s)"
else
  echo "WARN: UPLOAD_DIR が存在しません: $UPLOAD_DIR (アップロード未作成なら正常)" >&2
fi

# 環境設定（シークレットを含むため root 以外読めない権限で保持）
if [[ -f "$ENV_FILE" ]]; then
  cp -a "$ENV_FILE" "$WORK/civilpdf.env"
  chmod 600 "$WORK/civilpdf.env"
fi

# 検証済みの内容だけを公開名へ移動する（失敗時に中途半端な snapshot を残さない）
mv "$WORK" "$DEST"
PUBLISHED=1
echo "Backup complete: $DEST"

# 保持期間より古いバックアップを削除する。検証済みの今回分が存在するときだけ
# 実行されるため、直近の正常バックアップが失われることはない。
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d \
  -name '.incomplete-*' -mtime +1 -exec rm -rf {} + 2>/dev/null || true
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d \
  -mtime +"$RETENTION_DAYS" ! -name "$DEST_NAME" -exec rm -rf {} + 2>/dev/null || true

exit 0
