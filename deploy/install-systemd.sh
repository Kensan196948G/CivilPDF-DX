#!/usr/bin/env bash
# deploy/install-systemd.sh
# Register the CivilPDF-DX OPS units (backup / monitor / restore-drill /
# retention) as systemd USER services.
#
# アプリ本体（backend/frontend/db）は docker compose スタックで稼働する。
# compose スタックと Tunnel は「system units」で動く:
#   /etc/systemd/system/civilpdf-dx.service            (docker compose up -d)
#   /etc/systemd/system/civilpdf-dx-cloudflared.service (cloudflared tunnel)
# → これらは root 権限でインストールする（内容は docs/operations/runbook.md §1）。
#
# このスクリプトが登録するのは「運用系」ユーザーユニットのみ:
#   civilpdf-backup.timer        毎日 02:30 JST 本番バックアップ（compose db を pg_dump）
#   civilpdf-monitor.timer       5 分毎ヘルスチェック（nginx 18970 + in-container readiness + バックアップ鮮度）
#   civilpdf-restore-drill.timer 四半期 復元訓練（civildx_drill へ復元して起動・認証まで検証）
#   civilpdf-retention.timer     保持期限/GDPR 削除パス（※有効化は明示的な運用判断）
#
# Run as the kensan user (NOT root) — uses systemd --user mode.

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/deploy"
UNIT_DIR="$HOME/.config/systemd/user"
ENV_DIR="$HOME/.config/civilpdf"

echo "==> Creating directories"
mkdir -p "$UNIT_DIR" "$ENV_DIR"

echo "==> Copying ops unit files"
cp "$DEPLOY_DIR/civilpdf-backup.service" "$UNIT_DIR/"
cp "$DEPLOY_DIR/civilpdf-backup.timer" "$UNIT_DIR/"
cp "$DEPLOY_DIR/civilpdf-monitor.service" "$UNIT_DIR/"
cp "$DEPLOY_DIR/civilpdf-monitor.timer" "$UNIT_DIR/"
cp "$DEPLOY_DIR/civilpdf-restore-drill.service" "$UNIT_DIR/"
cp "$DEPLOY_DIR/civilpdf-restore-drill.timer" "$UNIT_DIR/"
# Retention / GDPR deletion timer: copied but NOT enabled automatically. It
# physically deletes documents whose deletion a user requested more than
# --grace-days ago, so enabling it is a deliberate operator decision.
cp "$DEPLOY_DIR/civilpdf-retention.service" "$UNIT_DIR/"
cp "$DEPLOY_DIR/civilpdf-retention.timer" "$UNIT_DIR/"

# --- 旧構成（ホスト uvicorn 8180 / vite preview 5182 / user tunnel）の退役 -----
# 2026-09-18 時点で本番は docker compose へ移行済み。旧ユニットが残っている
# ホストでは退役させる（手順: docs/operations/runbook.md §2.1）。
for legacy in civilpdf-backend.service civilpdf-frontend.service civilpdf-cloudflared.service; do
  if [[ -f "$UNIT_DIR/$legacy" ]]; then
    echo "==> RETIRED legacy unit present: $legacy"
    echo "    Run to retire:  systemctl --user disable --now $legacy"
    echo "    Then remove:    rm $UNIT_DIR/$legacy && systemctl --user daemon-reload"
  fi
done

# 本番 env（drill 用 SECRET_KEY 等・host-side）。DATABASE_URL は compose 本番では
# 使用しない（db コンテナ内で完結）。バックアップのシークレット保存は compose の .env。
if [[ ! -f "$ENV_DIR/civilpdf.env" ]]; then
  echo "==> Creating env file from example (edit it before starting the services)"
  install -m 600 "$DEPLOY_DIR/civilpdf.env.example" "$ENV_DIR/civilpdf.env"
  echo "    >> Edit $ENV_DIR/civilpdf.env with real secrets (SECRET_KEY etc.) <<"
fi

echo "==> Reloading systemd user daemon"
systemctl --user daemon-reload

echo "==> Enabling ops timers"
systemctl --user enable civilpdf-backup.timer civilpdf-monitor.timer civilpdf-restore-drill.timer

echo ""
echo "Done. To start now:"
echo "  systemctl --user start civilpdf-backup.timer civilpdf-monitor.timer civilpdf-restore-drill.timer"
echo ""
echo "Retention / GDPR deletion (OPT-IN — physically deletes files):"
echo "  # dry-run first, then enable:"
echo "  cd <production checkout> && docker compose -f docker-compose.prod.yml cp scripts/retention-job.py backend:/tmp/"
echo "  docker compose -f docker-compose.prod.yml exec -T backend sh -c 'PYTHONPATH=/app python /tmp/retention-job.py --dry-run'"
echo "  systemctl --user enable --now civilpdf-retention.timer"
echo ""
echo "To enable lingering (run without being logged in):"
echo "  sudo loginctl enable-linger $(id -un)"
echo ""
echo "URL: https://civilpdf.mirai-dx-platform.com"
