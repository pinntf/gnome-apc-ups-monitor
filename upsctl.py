#!/usr/bin/env python3
"""Manage user-local APC UPS widget configuration."""
import argparse
import ipaddress
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CONFIG = Path.home() / '.config/apc-ups-desktop-widget/config.json'
DEFAULT = {'interval_seconds': 30, 'devices': []}


def load():
    if not CONFIG.exists():
        return {'interval_seconds': 30, 'devices': []}
    data = json.loads(CONFIG.read_text(encoding='utf-8'))
    if not isinstance(data.get('devices'), list):
        raise ValueError('Invalid configuration: devices must be a list')
    return data


def save(data):
    CONFIG.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(CONFIG.parent, 0o700)
    fd, name = tempfile.mkstemp(prefix='.config-', dir=CONFIG.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            os.fchmod(f.fileno(), 0o600)
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        os.replace(name, CONFIG)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def check_host(host):
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        if len(host) > 253 or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', host) or '..' in host:
            raise ValueError('Enter a valid IP address or DNS hostname')
        return host


def reload_service():
    result = subprocess.run(['systemctl', '--user', 'try-restart', 'apc-ups-desktop-widget.service'], check=False, capture_output=True, text=True)
    if result.returncode:
        print('Note: service was not restarted. Run: systemctl --user restart apc-ups-desktop-widget.service', file=sys.stderr)


def add(args):
    data = load()
    host = check_host(args.ip)
    if not (1 <= args.port <= 65535):
        raise ValueError('Port must be between 1 and 65535')
    if not args.community or '\n' in args.community:
        raise ValueError('SNMP community must not be empty or multiline')
    if any(x['ip'].lower() == host.lower() and int(x.get('port', 161)) == args.port for x in data['devices']):
        raise ValueError(f'UPS {host}:{args.port} is already configured')
    label = args.name or f'UPS-{len(data["devices"]) + 1:02d}'
    data['devices'].append({'label': label, 'ip': host, 'port': args.port, 'community': args.community})
    save(data)
    reload_service()
    print(f'Added {label} ({host}:{args.port})')


def remove(args):
    data = load()
    matches = [d for d in data['devices'] if d['ip'] == args.target or d.get('label') == args.target]
    if not matches:
        raise ValueError('UPS not found (use list to see names and IPs)')
    if len(matches) > 1:
        raise ValueError('More than one UPS matches; use its IP address')
    data['devices'].remove(matches[0])
    save(data)
    reload_service()
    print(f'Removed {matches[0].get("label", matches[0]["ip"])}')


def listing(_args):
    data = load()
    print(f'Polling interval: {data.get("interval_seconds", 30)} seconds')
    if not data['devices']:
        print('No UPS devices. Add one with: apc-ups-widget add')
    for d in data['devices']:
        print(f'  {d.get("label", d["ip"])}   {d["ip"]}:{d.get("port", 161)}')


def interval(args):
    if not 10 <= args.seconds <= 3600:
        raise ValueError('Interval must be 10–3600 seconds')
    data = load()
    data['interval_seconds'] = args.seconds
    save(data)
    reload_service()
    print(f'Polling interval set to {args.seconds}s')


def interactive_add():
    name = input('UPS name [UPS-01]: ').strip() or 'UPS-01'
    ip = input('UPS IP address or hostname: ').strip()
    port_s = input('SNMP port [161]: ').strip()
    community = input('SNMP v2c community [public]: ').strip() or 'public'
    add(argparse.Namespace(name=name, ip=ip, port=int(port_s or '161'), community=community))


def main():
    parser = argparse.ArgumentParser(prog='apc-ups-widget', description='Manage APC UPS GNOME desktop widget')
    sub = parser.add_subparsers(dest='action')
    a = sub.add_parser('add', help='Add an UPS (interactive if --ip omitted)')
    a.add_argument('--name', help='Display name')
    a.add_argument('--ip', help='IP address / DNS hostname')
    a.add_argument('--port', type=int, default=161)
    a.add_argument('--community', default='public')
    r = sub.add_parser('remove', help='Remove an UPS by name or IP')
    r.add_argument('target')
    sub.add_parser('list', help='List devices (no credentials displayed)')
    i = sub.add_parser('interval', help='Set polling interval')
    i.add_argument('seconds', type=int)
    args = parser.parse_args()
    try:
        if args.action == 'add':
            interactive_add() if args.ip is None else add(args)
        elif args.action == 'remove':
            remove(args)
        elif args.action == 'list':
            listing(args)
        elif args.action == 'interval':
            interval(args)
        else:
            parser.print_help()
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
