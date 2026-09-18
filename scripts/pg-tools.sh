#!/usr/bin/env bash
#
# Shared PostgreSQL client-tool selection for the CivilPDF-DX ops scripts.
#
# pg_dump / pg_restore must come from the same major version as the **server**.
# A dump written by a newer pg_dump uses an archive format the older client
# cannot read. Observed on 2026-09-18 on this host: backups were written with
# pg_dump 18 while the default pg_restore was 16, so the restore procedure
# failed with
#   pg_restore: エラー: ファイルヘッダ内のバージョン(1.16)はサポートされていません
# The host has several majors installed (16/17/18) and PATH is mixed
# (psql 18, pg_dump 17, pg_restore 16), so "newest installed binary" is the
# wrong choice — match the server instead.
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]}")/pg-tools.sh"
#   PG_BIN="$(select_pg_bin pg_dump "$DATABASE_URL")" || exit 1

# Print the server's major version (e.g. 16) for a libpq URL, or nothing.
pg_server_major() {
  local url="$1" version
  version="$(psql "$url" -tAc 'show server_version' 2>/dev/null | cut -d. -f1)"
  if [[ "$version" =~ ^[0-9]+$ ]]; then
    printf '%s\n' "$version"
  fi
}

# Print the bin directory holding $tool for the server behind $url.
# Prefers the exactly-matching major, then falls back to PATH.
select_pg_bin() {
  local tool="$1" url="$2" major dir
  major="$(pg_server_major "$url")"
  if [[ -n "$major" ]]; then
    dir="/usr/lib/postgresql/${major}/bin"
    if [[ -x "${dir}/${tool}" ]]; then
      printf '%s\n' "$dir"
      return 0
    fi
  fi
  if command -v "$tool" >/dev/null 2>&1; then
    dir="$(dirname "$(command -v "$tool")")"
    printf '%s\n' "$dir"
    return 0
  fi
  return 1
}

# Warn (to stderr) when the chosen client's major differs from the server's.
warn_on_version_mismatch() {
  local tool_path="$1" url="$2" client_major server_major
  client_major="$("$tool_path" --version 2>/dev/null | grep -oE '[0-9]+' | head -1)"
  server_major="$(pg_server_major "$url")"
  if [[ -n "$client_major" && -n "$server_major" && "$client_major" != "$server_major" ]]; then
    echo "WARN: $(basename "$tool_path") major ${client_major} != server major ${server_major};" \
         "ダンプ/復元の互換性に注意してください" >&2
  fi
}

# Choose a pg_restore for a SPECIFIC dump file.
#
# For restore the constraint is different from backup: the client must be able to
# *read the archive*, and (because a newer pg_restore can restore into an older
# server, but not the reverse) the server-matching client is not always usable.
# A dump produced before the move away from Neon is archive format 1.16 (PG 18)
# and the PG 16 client cannot read it at all, so falling back to a newer client
# is the only way to restore it.
select_pg_restore_for_dump() {
  local dump="$1" url="$2" major dir
  major="$(pg_server_major "$url")"

  # 1) the server-matching client, when it can read this dump
  if [[ -n "$major" && -x "/usr/lib/postgresql/${major}/bin/pg_restore" ]]; then
    if "/usr/lib/postgresql/${major}/bin/pg_restore" --list "$dump" >/dev/null 2>&1; then
      printf '%s\n' "/usr/lib/postgresql/${major}/bin"
      return 0
    fi
  fi

  # 2) otherwise the newest installed client that can read it
  local candidates=()
  while IFS= read -r dir; do
    [[ -n "$dir" ]] && candidates+=("$dir")
  done < <(ls -1d /usr/lib/postgresql/*/bin 2>/dev/null | sort -Vr)
  if command -v pg_restore >/dev/null 2>&1; then
    candidates+=("$(dirname "$(command -v pg_restore)")")
  fi

  for dir in "${candidates[@]}"; do
    if [[ -x "${dir}/pg_restore" ]] && "${dir}/pg_restore" --list "$dump" >/dev/null 2>&1; then
      printf '%s\n' "$dir"
      return 0
    fi
  done
  return 1
}
