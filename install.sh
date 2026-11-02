#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UUID='apc-ups-desktop-widget@local'
APP="$HOME/.local/share/apc-ups-desktop-widget"
EXT="$HOME/.local/share/gnome-shell/extensions/$UUID"
CFG="$HOME/.config/apc-ups-desktop-widget"
BIN="$HOME/.local/bin"
if [[ $EUID -eq 0 ]]; then
  echo 'Run this as your regular desktop user, not root.' >&2
  exit 1
fi
for command in python3 snmpget systemctl; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Missing dependency: $command" >&2
    echo 'Fedora: sudo dnf install net-snmp-utils python3' >&2
    echo 'Ubuntu/Debian: sudo apt install snmp python3' >&2
    echo 'Arch: sudo pacman -S net-snmp python' >&2
    exit 1
  fi
done
mkdir -p "$APP" "$EXT" "$CFG" "$BIN" "$HOME/.config/systemd/user"
chmod 700 "$CFG"
cp "$ROOT/collector.py" "$APP/collector.py"
cp "$ROOT/upsctl.py" "$APP/upsctl.py"
cp "$ROOT/extension/"* "$EXT/"
cat > "$BIN/apc-ups-widget" <<EOF
#!/usr/bin/env bash
exec /usr/bin/env python3 "$APP/upsctl.py" "\$@"
EOF
chmod 755 "$BIN/apc-ups-widget"
if [[ ! -f "$CFG/config.json" ]]; then
  printf '{"interval_seconds": 30, "devices": []}\n' > "$CFG/config.json"
  chmod 600 "$CFG/config.json"
  echo 'Configure your first UPS:'
  python3 "$APP/upsctl.py" add
  while true; do
    read -r -p 'Add another UPS? [y/N]: ' more || break
    case "$more" in y|Y|yes|YES) python3 "$APP/upsctl.py" add ;; *) break ;; esac
  done
else
  chmod 600 "$CFG/config.json"
  echo "Existing configuration kept: $CFG/config.json"
fi
cat > "$HOME/.config/systemd/user/apc-ups-desktop-widget.service" <<EOF
[Unit]
Description=APC UPS SNMP polling for GNOME desktop
After=network-online.target
[Service]
ExecStart=/usr/bin/env python3 $APP/collector.py
Restart=always
RestartSec=5
[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now apc-ups-desktop-widget.service
systemctl --user restart apc-ups-desktop-widget.service
if command -v gnome-extensions >/dev/null 2>&1; then
  gnome-extensions disable "$UUID" >/dev/null 2>&1 || true
  gnome-extensions enable "$UUID" >/dev/null 2>&1 || true
fi
printf '\nInstalled. Commands: %s/apc-ups-widget list | add | remove | interval\n' "$BIN"
echo "Configuration: $CFG/config.json"
echo 'If the widget is not visible, log out and back into GNOME, then enable the extension.'
