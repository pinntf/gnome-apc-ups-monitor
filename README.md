# GNOME APC UPS Monitor

A draggable GNOME Shell desktop widget for monitoring **multiple APC Smart-UPS devices** via SNMP v2c.

GNOME APC UPS Monitor displays battery charge, UPS load, remaining runtime, input/output voltage, temperature, battery health, replacement date, and self-test information.

The widget automatically detects and displays UPS devices from your configuration file. You can add or remove UPS devices at any time without reinstalling the extension.

## Features

- Monitor multiple APC Smart-UPS devices simultaneously
- Real-time monitoring via SNMP v2c
- Battery charge and UPS load indicators
- Input and output voltage monitoring
- Remaining battery runtime
- UPS temperature and battery health
- Battery replacement and self-test information
- Draggable desktop widget with persistent positioning
- Automatic startup using systemd
- Interactive installation and configuration
- Add or remove UPS devices without reinstalling
- Configurable monitoring interval

## Requirements

- GNOME Shell 45–50 (declared supported versions; compatibility may vary)
- Python 3
- Net-SNMP (`snmpget`)
- systemd user services
- APC Smart-UPS with an accessible SNMP agent supporting APC PowerNet MIB OIDs
- SNMP v2c read community

### Install dependencies

**Fedora**
```bash
sudo dnf install python3 net-snmp-utils
```

**Ubuntu / Debian**
```bash
sudo apt install python3 snmp
```

**Arch Linux**
```bash
sudo pacman -S python net-snmp
```

## Installation

Clone the repository:

```bash
git clone https://github.com/pinntf/gnome-apc-ups-monitor.git
cd gnome-apc-ups-monitor
bash install.sh
```

Run the installer as your regular desktop user, **without `sudo`**.

During installation, you will be prompted to enter:

- UPS name (e.g. `UPS-01`)
- UPS IP address (e.g. `192.168.1.100`)
- SNMP port (default: `161`)
- SNMP v2c community (default: `public`)

The installer also allows you to add additional UPS devices.

Existing configuration is preserved during upgrades.

If the widget does not appear immediately, log out and log back in, then enable the extension using GNOME Extensions.

## Managing UPS Devices

GNOME APC UPS Monitor includes a command-line configuration utility.

**List configured UPS devices**
```bash
~/.local/bin/apc-ups-widget list
```

**Add a new UPS**
```bash
~/.local/bin/apc-ups-widget add
```

**Add a UPS with specific parameters**
```bash
~/.local/bin/apc-ups-widget add --name 'UPS-03' --ip 192.168.1.30
```

**Remove a UPS**
```bash
~/.local/bin/apc-ups-widget remove UPS-03
```

**Change the monitoring interval**
```bash
~/.local/bin/apc-ups-widget interval 30
```

The configuration utility automatically restarts the monitoring service when needed.

The desktop widget checks cached measurements every five seconds. Updated device information appears after the next polling cycle.

## Configuration Files

| File | Location |
|---|---|
| Configuration | `~/.config/apc-ups-desktop-widget/config.json` |
| Cached measurements | `~/.cache/apc-ups-desktop-widget/ups.json` |
| Widget position | `~/.config/apc-ups-desktop-widget/position.json` |
| systemd service | `~/.config/systemd/user/apc-ups-desktop-widget.service` |

The configuration file is stored with private permissions (`0600`).

## Service Management

**Check service status**
```bash
systemctl --user status apc-ups-desktop-widget.service
```

**Restart monitoring**
```bash
systemctl --user restart apc-ups-desktop-widget.service
```

**View live logs**
```bash
journalctl --user -u apc-ups-desktop-widget.service -f
```

## Uninstallation

Run:

```bash
bash uninstall.sh
```

The uninstaller removes the application components but preserves your UPS configuration and saved widget position for future installations.

To completely reset the configuration, manually remove:

```bash
rm -rf ~/.config/apc-ups-desktop-widget
rm -rf ~/.cache/apc-ups-desktop-widget
```

## Security

GNOME APC UPS Monitor uses SNMP v2c.

**Important:** SNMP v2c does not encrypt community strings or monitoring traffic.

For improved security:

- Use a dedicated read-only SNMP community
- Restrict SNMP access to trusted management networks
- Avoid exposing SNMP port `161/UDP` to the public internet
- Never commit configuration files containing real IP addresses or community strings

The repository does not contain real UPS addresses or credentials.

## Compatibility

GNOME APC UPS Monitor is designed for Linux desktops running GNOME Shell.

The widget uses a vertical layout to display multiple UPS devices. Adding many devices may increase the widget height beyond the available screen space.

## License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.
