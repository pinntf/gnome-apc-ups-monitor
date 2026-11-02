#!/usr/bin/env bash
set -euo pipefail
UUID='apc-ups-desktop-widget@local'
gnome-extensions disable "$UUID" || true
systemctl --user disable --now apc-ups-desktop-widget.service || true
rm -f "$HOME/.config/systemd/user/apc-ups-desktop-widget.service"
rm -rf "$HOME/.local/share/apc-ups-desktop-widget" "$HOME/.local/share/gnome-shell/extensions/$UUID"
systemctl --user daemon-reload
echo 'Removed UPS widget; configuration retained in ~/.config/apc-ups-desktop-widget'
