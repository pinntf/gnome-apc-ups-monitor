#!/usr/bin/env python3
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
CONFIG = HOME / '.config/apc-ups-desktop-widget/config.json'
CACHE = HOME / '.cache/apc-ups-desktop-widget/ups.json'
BASE = '1.3.6.1.4.1.318.1.1.1'
OIDS = {
    'model': '1.1.1',
    'name': '1.1.2',
    'battery_status': '2.1.1',
    'battery_replace_date': '2.1.3',
    'selftest_result': '7.2.3',
    'selftest_date': '7.2.4',
    'battery': '2.2.1',
    'temperature': '2.2.2',
    'runtime': '2.2.3',
    'replace': '2.2.4',
    'input_voltage': '3.2.1',
    'output_status': '4.1.1',
    'output_voltage': '4.2.1',
    'load': '4.2.3',
    'output_current': '4.2.4',
}
STATUS = {1: 'UNKNOWN', 2: 'ONLINE', 3: 'ON BATTERY', 4: 'BOOST', 5: 'SLEEP', 6: 'OFF', 7: 'REBOOT', 8: 'ECO', 9: 'BYPASS', 10: 'TRIM'}


def read_config():
    return json.loads(CONFIG.read_text(encoding='utf-8'))


def poll(item):
    host = item['ip']
    port = int(item.get('port', 161))
    community = item.get('community', 'public')
    requested = {'.' + BASE + '.' + suffix + '.0': name for name, suffix in OIDS.items()}
    cmd = ['snmpget', '-v2c', '-On', '-t', '2', '-r', '0', '-c', community, f'udp:{host}:{port}', *requested.keys()]
    result = {'ip': host, 'label': item.get('label', host), 'online': False, 'updated': datetime.now(timezone.utc).isoformat()}
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=7)
        for line in p.stdout.splitlines():
            if ' = ' not in line:
                continue
            oid, raw = line.split(' = ', 1)
            key = requested.get(oid.strip())
            if not key or 'No Such' in raw:
                continue
            m = re.search(r'(?:INTEGER|Gauge32|Counter32):\s*(-?\d+)', raw)
            if m:
                value = int(m.group(1))
            elif 'Timeticks:' in raw:
                m = re.search(r'Timeticks:\s*\((\d+)\)', raw)
                value = int(m.group(1)) if m else None
            elif 'STRING:' in raw:
                value = raw.split('STRING:', 1)[1].strip().strip('"')
            else:
                value = None
            if value is not None:
                result[key] = value
        result['online'] = 'battery' in result or 'output_status' in result
        if result['online']:
            result['status'] = STATUS.get(result.get('output_status'), 'UNKNOWN')
            result['runtime_min'] = round(result['runtime'] / 6000) if isinstance(result.get('runtime'), int) else None
            result['battery_ok'] = result.get('battery_status') == 2
            result['health'] = ('REPLACE' if result.get('replace') == 2 else
                                'WARNING' if result.get('battery_status') in (3, 4, 5) else
                                'NORMAL' if result.get('replace') == 1 and result.get('battery_status') == 2 else 'UNKNOWN')
            result['selftest'] = {1: 'OK', 2: 'FAILED', 3: 'INVALID', 4: 'RUNNING'}.get(result.get('selftest_result'), 'UNKNOWN')
            date_raw = result.get('battery_replace_date')
            result['battery_age_months'] = None
            if isinstance(date_raw, str):
                try:
                    parsed = datetime.strptime(date_raw, '%m/%d/%Y' if len(date_raw.split('/')[-1]) == 4 else '%m/%d/%y')
                    today = datetime.now().date()
                    result['battery_age_months'] = max(0, (today.year - parsed.year) * 12 + today.month - parsed.month - (today.day < parsed.day))
                except ValueError:
                    pass
            result['alert'] = result.get('output_status') == 3 or result['health'] in ('REPLACE', 'WARNING') or result['selftest'] == 'FAILED'
        else:
            result['error'] = (p.stderr or p.stdout or 'No SNMP values').strip()[:180]
    except (OSError, subprocess.TimeoutExpired) as exc:
        result['error'] = str(exc)[:180]
    return result


def main():
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            config = read_config()
            data = {'updated': datetime.now(timezone.utc).isoformat(), 'devices': [poll(item) for item in config['devices']]}
            tmp = CACHE.with_suffix('.tmp')
            tmp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
            os.replace(tmp, CACHE)
            time.sleep(max(10, int(config.get('interval_seconds', 30))))
        except Exception as exc:
            print('Collector error:', exc, flush=True)
            time.sleep(30)


if __name__ == '__main__':
    main()
