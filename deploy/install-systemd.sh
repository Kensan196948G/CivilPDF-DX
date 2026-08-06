#!/usr/bin/env bash
# deploy/install-systemd.sh
# Register CivilPDF-DX backend + frontend + Cloudflare Tunnel + backup timer
# as systemd user services.
# Run as the kensan user (NOT root) — uses systemd --user mode.

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"
ENV_DIR="$HOME/.config/civilpdf"

echo "==> Creating directories"
mkdir -p "$UNIT_DIR" "$ENV_DIR"

echo "==> Copying service files"
cp "$DEPLOY_DIR/civilpdf-backend.service" "$UNIT_DIR/"
cp "$DEPLOY_DIR/civilpdf-frontend.service" "$UNIT_DIR/"
cp "$DEPLOY_DIR/civilpdf-cloudflared.service" "$UNIT_DIR/"
cp "$DEPLOY_DIR/civilpdf-backup.service" "$UNIT_DIR/"
cp "$DEPLOY_DIR/civilpdf-backup.timer" "$UNIT_DIR/"
cp "$DEPLOY_DIR/civilpdf-monitor.service" "$UNIT_DIR/"
cp "$DEPLOY_DIR/civilpdf-monitor.timer" "$UNIT_DIR/"
cp "$DEPLOY_DIR/civilpdf-restore-drill.service" "$UNIT_DIR/"
cp "$DEPLOY_DIR/civilpdf-restore-drill.timer" "$UNIT_DIR/"

# Create env file from example if it doesn't exist
ENV_FILE="$ENV_DIR/civilpdf.env"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "==> Creating env file from example (edit it before starting the services)"
    install -m 600 "$DEPLOY_DIR/civilpdf.env.example" "$ENV_FILE"
    echo "    >> Edit $ENV_FILE with real secrets (SECRET_KEY etc.) <<"
fi

# Tunnel config — credentials JSON は `cloudflared tunnel create` が生成する秘密情報
if [[ ! -f "$HOME/.cloudflared/civilpdf-config.yml" ]]; then
    echo "==> NOTE: ~/.cloudflared/civilpdf-config.yml がありません"
    echo "    docs/deployment/webui-cloudflare-tunnel.md の手順でトンネルを作成してください"
fi

echo "==> Reloading systemd user daemon"
systemctl --user daemon-reload

echo "==> Enabling services (start on login / linger)"
systemctl --user enable civilpdf-backend civilpdf-frontend civilpdf-cloudflared \
  civilpdf-backup.timer civilpdf-monitor.timer civilpdf-restore-drill.timer

echo ""
echo "Done. To start now:"
echo "  systemctl --user start civilpdf-backend civilpdf-frontend civilpdf-cloudflared"
echo "  systemctl --user start civilpdf-backup.timer civilpdf-monitor.timer civilpdf-restore-drill.timer"
echo ""
echo "To enable lingering (run without being logged in):"
echo "  sudo loginctl enable-linger $(id -un)"
echo ""
echo "URL: https://civilpdf.mirai-dx-platform.com"
