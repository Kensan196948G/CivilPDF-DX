#!/usr/bin/env bash
#
# CivilPDF-DX — external alert notification (email via msmtp)
#
# Sends an email through the user's configured msmtp account (default Gmail).
# Subject/body are read from arguments / stdin so any script can use it.
#
# Usage:
#   ./scripts/alert-notify.sh "SUBJECT" "BODY"
#   printf 'body\n' | ./scripts/alert-notify.sh "SUBJECT"
#   ./scripts/alert-notify.sh --test            # send a test alert
#
# Environment:
#   CIVILPDF_ALERT_TO   recipient (default: msmtp account owner kensan1969@gmail.com)
#   CIVILPDF_ALERT_FROM sender (default: same as recipient)
#
set -uo pipefail

TO="${CIVILPDF_ALERT_TO:-kensan1969@gmail.com}"
FROM="${CIVILPDF_ALERT_FROM:-$TO}"
SUBJECT="${1:-CivilPDF-DX Alert}"
BODY=""

if [[ "${1:-}" == "--test" ]]; then
  SUBJECT="[CivilPDF-DX] テスト通知 (alert-notify)"
  BODY="これは alert-notify.sh のテスト通知です。
日時: $(date '+%Y-%m-%d %H:%M:%S %Z')
ホスト: $(hostname)
送信は成功しました。設定は正常です。"
else
  shift 2>/dev/null || true
  if [[ $# -ge 1 ]]; then
    BODY="$*"
  else
    BODY="$(cat)"
  fi
fi

if ! command -v msmtp >/dev/null 2>&1; then
  echo "ERROR: msmtp not found" >&2
  exit 2
fi

{
  printf 'To: %s\n' "$TO"
  printf 'From: %s\n' "$FROM"
  printf 'Subject: %s\n' "$SUBJECT"
  printf 'Date: %s\n' "$(date -R)"
  printf 'MIME-Version: 1.0\n'
  printf 'Content-Type: text/plain; charset=UTF-8\n'
  printf 'Content-Transfer-Encoding: 8bit\n'
  printf '\n%s\n' "$BODY"
} | msmtp --read-envelope-from -t

rc=$?
if [[ $rc -eq 0 ]]; then
  echo "alert sent to $TO: $SUBJECT"
else
  echo "ERROR: msmtp failed (rc=$rc)" >&2
  exit 1
fi
