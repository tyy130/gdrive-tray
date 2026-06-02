#!/usr/bin/env bash
# gdrive-tray — one-shot installer
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo ""
echo "  gdrive-tray installer"
echo ""

# 1. Python venv
if [ ! -d ".venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv --system-site-packages .venv
fi

source .venv/bin/activate
echo "  Installing Python packages..."
pip install pillow numpy --quiet
python3 -c "from PIL import Image; import numpy; print('  Packages verified')"

# 2. System deps check
for cmd in rclone fusermount notify-send; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "  WARNING: '$cmd' not found — install it before running"
    fi
done

# 3. Desktop entry
DESKTOP_FILE="$HOME/.local/share/applications/gdrive-tray.desktop"
mkdir -p "$(dirname "$DESKTOP_FILE")"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=GDrive Tray
Comment=Google Drive system tray mount manager
Exec=$DIR/.venv/bin/python3 $DIR/gdrive-tray.py
Icon=$DIR/gdrive-icon.png
Terminal=false
Categories=Utility;Network;FileTransfer;
Keywords=google;drive;gdrive;rclone;mount;tray;
StartupNotify=false
EOF

# 4. Autostart entry
AUTOSTART_FILE="$HOME/.config/autostart/gdrive-tray.desktop"
mkdir -p "$(dirname "$AUTOSTART_FILE")"
cp "$DESKTOP_FILE" "$AUTOSTART_FILE"
echo "X-GNOME-Autostart-enabled=true" >> "$AUTOSTART_FILE"

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo ""
echo "  Installed!"
echo ""
echo "  Find 'GDrive Tray' in your app menu"
echo "  Auto-starts on login"
echo ""
echo "  Starting now..."
echo ""

# 5. Launch
nohup "$DIR/.venv/bin/python3" "$DIR/gdrive-tray.py" > /tmp/gdrive-tray.log 2>&1 &
echo "  Running (PID $!)"
