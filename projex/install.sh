#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APP_ID="io.github.emmastf.Projex"
ICON_SRC="$SCRIPT_DIR/icons/$APP_ID.svg"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
DESKTOP_DIR="$HOME/.local/share/applications"
APP_EXEC="python3 $SCRIPT_DIR/app.py"

# ── 1. System dependencies ────────────────────────────────────────────────────
echo "Installing system dependencies..."
if command -v zypper &>/dev/null; then
    sudo zypper install -y python3-gobject typelib-1_0-Gtk-4_0 typelib-1_0-Adw-1 \
         librsvg2-tools 2>/dev/null || true
elif command -v dnf &>/dev/null; then
    sudo dnf install -y python3-gobject gtk4 libadwaita librsvg2-tools
elif command -v apt-get &>/dev/null; then
    sudo apt-get install -y python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 librsvg2-bin
else
    echo "WARNING: Unknown package manager. Install python3-gi, gtk4, libadwaita manually."
fi

# ── 2. Icon ───────────────────────────────────────────────────────────────────
echo "Installing icon..."
mkdir -p "$ICON_DIR"
cp "$ICON_SRC" "$ICON_DIR/$APP_ID.svg"

# Also install PNG sizes for maximum compatibility
if command -v rsvg-convert &>/dev/null; then
    for SIZE in 16 32 48 64 128 256; do
        PNG_DIR="$HOME/.local/share/icons/hicolor/${SIZE}x${SIZE}/apps"
        mkdir -p "$PNG_DIR"
        rsvg-convert -w "$SIZE" -h "$SIZE" "$ICON_SRC" -o "$PNG_DIR/$APP_ID.png"
    done
fi

# Refresh icon cache
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

# ── 3. Desktop entry ──────────────────────────────────────────────────────────
echo "Installing desktop entry..."
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/$APP_ID.desktop" <<EOF
[Desktop Entry]
Name=Projex
GenericName=Project Tracker
Comment=Track projects, milestones, tasks, goals, and writing
Exec=$APP_EXEC
Icon=$APP_ID
Terminal=false
Type=Application
Categories=Office;ProjectManagement;GTK;
Keywords=project;tasks;milestones;goals;tracker;
StartupWMClass=projex
EOF

# Refresh desktop database
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

echo ""
echo "Done!"
echo "  Run directly:  python3 $SCRIPT_DIR/app.py"
echo "  Or launch from your app grid / application menu."
