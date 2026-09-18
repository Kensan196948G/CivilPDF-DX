#!/usr/bin/env bash
#
# CivilPDF-DX — production backup (docker compose PostgreSQL / host PostgreSQL / SQLite + uploads + env)
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
# Modes (CIVILPDF_DEPLOY_MODE, default auto-detect):
#   compose       本番が docker compose（docker-compose.prod.yml）で稼働している場合。
#                 db サービスのコンテナ内 pg_dump でダンプを作成する（認証情報不要・
#                 サーバーとクライアントの版数は必ず一致する）。uploads は backend
#                 コンテナ内の /app/uploads（named volume）から tar を取得する。
#                 シークレットは compose の .env を保存する。
#   database-url  DATABASE_URL（postgres*）でホスト PostgreSQL へ直接接続する
#                 従来モード。systemd/uvicorn でホスト PG を使う構成向け。
#   sqlite        SQLite ファイルのオンラインバックアップ。
#
# Usage:
#   ./scripts/backup-production.sh            # full backup + prune (auto mode)
#   CIVILPDF_DEPLOY_MODE=compose ./scripts/backup-production.sh
#   BACKUP_ROOT=/mnt/backup ./scripts/backup-production.sh
#
# Restore（compose 本番）:
#   1. cd <production checkout> && docker compose -f docker-compose.prod.yml stop backend
#   2. cat <BACKUP_ROOT>/<stamp>/civilpdf.dump | \
#        docker compose -f docker-compose.prod.yml exec -T db \
#        pg_restore -U civilpdf -d civilpdf --clean --if-exists --no-owner
#   3. cat <BACKUP_ROOT>/<stamp>/uploads.tar.gz | \
#        docker compose -f docker-compose.prod.yml exec -T backend \
#        tar xzf - -C /app/uploads
#   4. docker compose -f docker-compose.prod.yml start backend
#      （別ホストへの完全復元は docs/operations/runbook.md §3）
#
# Restore（ホスト PostgreSQL / SQLite 構成）:
#   1a. PostgreSQL: pg_restore --clean --if-exists --dbname "$DATABASE_URL" \
#          <BACKUP_ROOT>/<stamp>/civilpdf.dump
#   1b. SQLite: cp <BACKUP_ROOT>/<stamp>/civilpdf_dev.db <repo>/src/console/backend/
#
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
DB_PATH="${CIVILPDF_DB_PATH:-$PROJECT_DIR/src/console/backend/civilpdf_dev.db}"
UPLOAD_DIR="${CIVILPDF_UPLOAD_DIR:-$HOME/civildx/uploads}"
ENV_FILE="${CIVILPDF_ENV_FILE:-$HOME/.config/civilpdf/civilpdf.env}"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/civildx-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
DEPLOY_MODE="${CIVILPDF_DEPLOY_MODE:-auto}"

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

mkdir -p "$WORK"

# --- mode detection -----------------------------------------------------------
# 稼働中の compose スタックがあれば本番DBはその db コンテナ（2026-09-18 実測:
# 公開URL civilpdf.mirai-dx-platform.com は civilpdf-dx スタックが配信しており、
# audit_logs はそちらに書き込まれている。ホスト側 env の DATABASE_URL は旧構成）。
compose_db_running() {
  [[ -f "$COMPOSE_FILE" ]] || return 1
  local cid
  cid="$(docker compose -f "$COMPOSE_FILE" ps -q db 2>/dev/null || true)"
  [[ -n "$cid" ]] || return 1
  [[ "$(docker inspect -f '{{.State.Running}}' "$cid" 2>/dev/null || true)" == "true" ]]
}

MODE=""
if [[ "$DEPLOY_MODE" == "compose" ]]; then
  MODE="compose"
elif [[ "$DEPLOY_MODE" == "database-url" ]] || [[ "$DEPLOY_MODE" == "sqlite" ]]; then
  MODE="$DEPLOY_MODE"
elif [[ "$DEPLOY_MODE" == "auto" ]]; then
  if compose_db_running; then
    MODE="compose"
  else
    # ホスト env の DATABASE_URL（systemd/uvicorn 構成）
    if [[ -f "$ENV_FILE" ]]; then
      set -a
      # shellcheck disable=SC1090
      source "$ENV_FILE"
      set +a
    fi
    if [[ "${DATABASE_URL:-}" == postgres* ]]; then
      MODE="database-url"
    elif [[ -f "$DB_PATH" ]]; then
      MODE="sqlite"
    else
      echo "ERROR: DB not found (compose 未稼働・DATABASE_URL 未設定・$DB_PATH なし)" >&2
      exit 1
    fi
  fi
else
  echo "ERROR: invalid CIVILPDF_DEPLOY_MODE '$DEPLOY_MODE' (compose|database-url|sqlite|auto)" >&2
  exit 1
fi

if [[ "$MODE" == "compose" ]]; then
  # --- compose 本番: db コンテナ内の pg_dump（版数は必ずサーバーと一致）---------
  echo "PostgreSQL backup (docker compose): $COMPOSE_FILE db -> $WORK/civilpdf.dump"
  if ! docker compose -f "$COMPOSE_FILE" exec -T db \
      sh -lc 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" --format=custom' \
      >"$WORK/civilpdf.dump"; then
    echo "ERROR: compose pg_dump failed (db サービスが起動しているか確認してください)" >&2
    exit 1
  fi
  if [[ ! -s "$WORK/civilpdf.dump" ]]; then
    echo "ERROR: pg_dump produced an empty file" >&2
    exit 1
  fi
  # ①コンテナ内 pg_restore（サーバーと同一版数）で読めること
  if ! docker compose -f "$COMPOSE_FILE" exec -T db pg_restore --list \
      <"$WORK/civilpdf.dump" >/dev/null 2>&1; then
    echo "ERROR: in-container pg_restore cannot read the dump" >&2
    exit 1
  fi
  # ②ホストの既定 pg_restore（文書化された復元手順で使う）でも読めること
  if ! pg_restore --list "$WORK/civilpdf.dump" >/dev/null 2>&1; then
    echo "ERROR: 既定の pg_restore ($(pg_restore --version 2>/dev/null)) がこのダンプを読めません" >&2
    exit 1
  fi
  echo "PostgreSQL dump verified ($(stat -c %s "$WORK/civilpdf.dump") bytes, container+host pg_restore OK)"

  # --- compose 本番: uploads（named volume）を backend コンテナから tar で取得 --
  if ! docker compose -f "$COMPOSE_FILE" exec -T backend \
      tar czf - -C /app/uploads . >"$WORK/uploads.tar.gz" 2>/dev/null; then
    echo "ERROR: uploads archive from backend container failed" >&2
    exit 1
  fi
  echo "Uploads archived: $(stat -c %s "$WORK/uploads.tar.gz") bytes (uploads.tar.gz)"

  # --- compose 本番: シークレットは compose の .env ------------------------------
  if [[ -f "$PROJECT_DIR/.env" ]]; then
    cp -a "$PROJECT_DIR/.env" "$WORK/civilpdf.env"
    chmod 600 "$WORK/civilpdf.env"
    echo "Env saved: $PROJECT_DIR/.env -> civilpdf.env (0600)"
  else
    echo "WARN: $PROJECT_DIR/.env がありません（シークレットはバックアップされません）" >&2
  fi
elif [[ "$MODE" == "database-url" ]]; then
  # Select the client matching the SERVER's major version. Picking the newest
  # installed binary produced dumps the default pg_restore cannot read (see
  # scripts/pg-tools.sh).
  # shellcheck source=scripts/pg-tools.sh
  source "$PROJECT_DIR/scripts/pg-tools.sh"
  PG_BIN="$(select_pg_bin pg_dump "$DATABASE_URL")" || PG_BIN=""
  if [[ -z "$PG_BIN" ]]; then
    echo "ERROR: pg_dump がインストールされていません" >&2
    exit 1
  fi
  PG_DUMP="$PG_BIN/pg_dump"
  PG_RESTORE="$PG_BIN/pg_restore"
  echo "PostgreSQL backup: $PG_DUMP ($("$PG_DUMP" --version 2>/dev/null)) -> $WORK/civilpdf.dump"
  warn_on_version_mismatch "$PG_DUMP" "$DATABASE_URL"
  "$PG_DUMP" "$DATABASE_URL" --format=custom --file="$WORK/civilpdf.dump"
  "$PG_RESTORE" --list "$WORK/civilpdf.dump" >/dev/null
  if [[ ! -s "$WORK/civilpdf.dump" ]]; then
    echo "ERROR: pg_dump produced an empty file" >&2
    exit 1
  fi
  # The dump is only useful if the *default* client on this host can read it,
  # since that is what the documented restore procedure uses.
  if ! pg_restore --list "$WORK/civilpdf.dump" >/dev/null 2>&1; then
    echo "ERROR: 既定の pg_restore ($(pg_restore --version 2>/dev/null)) がこのダンプを読めません" >&2
    echo "       pg_dump と pg_restore のメジャーバージョンがサーバーと一致しているか確認してください" >&2
    exit 1
  fi
  echo "PostgreSQL dump verified ($(stat -c %s "$WORK/civilpdf.dump") bytes)"

  # ホスト側レイアウトの uploads
  mkdir -p "$WORK/uploads"
  if [[ -d "$UPLOAD_DIR" ]]; then
    cp -a "$UPLOAD_DIR"/. "$WORK/uploads/"
    echo "Uploads copied: $(find "$WORK/uploads" -type f | wc -l) file(s)"
  else
    echo "WARN: UPLOAD_DIR が存在しません: $UPLOAD_DIR (アップロード未作成なら正常)" >&2
  fi
  if [[ -f "$ENV_FILE" ]]; then
    cp -a "$ENV_FILE" "$WORK/civilpdf.env"
    chmod 600 "$WORK/civilpdf.env"
  fi
else
  # --- SQLite -------------------------------------------------------------------
  mkdir -p "$WORK/uploads"
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
  if [[ -d "$UPLOAD_DIR" ]]; then
    cp -a "$UPLOAD_DIR"/. "$WORK/uploads/"
    echo "Uploads copied: $(find "$WORK/uploads" -type f | wc -l) file(s)"
  else
    echo "WARN: UPLOAD_DIR が存在しません: $UPLOAD_DIR (アップロード未作成なら正常)" >&2
  fi
  if [[ -f "$ENV_FILE" ]]; then
    cp -a "$ENV_FILE" "$WORK/civilpdf.env"
    chmod 600 "$WORK/civilpdf.env"
  fi
fi

# 検証済みの内容だけを公開名へ移動する（失敗時に中途半端な snapshot を残さない）
mv "$WORK" "$DEST"
PUBLISHED=1
echo "Backup complete: $DEST (mode=$MODE)"

# 保持期間より古いバックアップを削除する。検証済みの今回分が存在するときだけ
# 実行されるため、直近の正常バックアップが失われることはない。
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d \
  -name '.incomplete-*' -mtime +1 -exec rm -rf {} + 2>/dev/null || true
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d \
  -mtime +"$RETENTION_DAYS" ! -name "$DEST_NAME" -exec rm -rf {} + 2>/dev/null || true

exit 0
