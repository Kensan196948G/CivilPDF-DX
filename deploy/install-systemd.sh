#!/usr/bin/env bash
# deploy/install-systemd.sh
# Register CivilPDF-DX backend + frontend as systemd user services.
# Run as the kensan user (NOT root) — uses systemd --user mode.

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"

echo "==> Creating systemd user unit directory: $UNIT_DIR"
mkdir -p "$UNIT_DIR"

echo "==> Copying service files"
cp "$DEPLOY_DIR/civilpdf-backend.service" "$UNIT_DIR/"
cp "$DEPLOY_DIR/civilpdf-frontend.service" "$UNIT_DIR/"

# Create env file from example if it doesn't exist
ENV_FILE="$DEPLOY_DIR/civilpdf.env"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "==> Creating env file from example (edit it before starting the services)"
    cp "$DEPLOY_DIR/civilpdf.env.example" "$ENV_FILE"
    echo "    >> Edit $ENV_FILE with real secrets <<"
fi

# Create upload dir
UPLOAD_DIR="/var/lib/civildx/uploads"
if [[ ! -d "$UPLOAD_DIR" ]]; then
    echo "==> Creating upload directory (requires sudo)"
    sudo mkdir -p "$UPLOAD_DIR"
    sudo chown "$(id -un):$(id -gn)" "$UPLOAD_DIR"
fi

echo "==> Reloading systemd user daemon"
systemctl --user daemon-reload

echo "==> Enabling services (start on login)"
systemctl --user enable civilpdf-backend.service civilpdf-frontend.service

echo ""
echo "Done. To start now:"
echo "  systemctl --user start civilpdf-backend civilpdf-frontend"
echo ""
echo "To enable lingering (run without being logged in):"
echo "  sudo loginctl enable-linger kensan"
echo ""
echo "Status:"
echo "  systemctl --user status civilpdf-backend civilpdf-frontend"
