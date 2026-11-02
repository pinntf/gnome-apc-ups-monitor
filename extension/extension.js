import St from 'gi://St';
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';

const CACHE = GLib.build_filenamev([GLib.get_home_dir(), '.cache', 'apc-ups-desktop-widget', 'ups.json']);
const POSITION = GLib.build_filenamev([GLib.get_home_dir(), '.config', 'apc-ups-desktop-widget', 'position.json']);


function readJSON(path, fallback) {
    try {
        const [ok, content] = GLib.file_get_contents(path);
        if (ok)
            return JSON.parse(new TextDecoder().decode(content));
    } catch (e) { }
    return fallback;
}

function label(text, styleClass = '', style = '') {
    const params = { text: String(text), y_align: Clutter.ActorAlign.CENTER };
    if (styleClass)
        params.style_class = styleClass;
    const item = new St.Label(params);
    if (style)
        item.set_style(style);
    return item;
}

function spacer() {
    return new St.Widget({ x_expand: true });
}

function fmt(value, suffix = '') {
    return value === null || value === undefined ? '--' : `${value}${suffix}`;
}

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

function prettyDateTime(iso) {
    if (!iso)
        return '--';
    try {
        const dt = GLib.DateTime.new_from_iso8601(iso, null);
        if (!dt)
            return '--';
        return dt.to_local().format('%-I:%M:%S %p');
    } catch (e) {
        return '--';
    }
}

function batteryAgeText(months) {
    if (!Number.isFinite(months))
        return '--';
    return `${Math.floor(months / 12)}y ${months % 12}m`;
}

function tempClass(temp) {
    if (!Number.isFinite(temp))
        return 'apc-temperature-unknown';
    if (temp >= 40)
        return 'apc-temperature-critical';
    if (temp >= 35)
        return 'apc-temperature-warning';
    return 'apc-temperature-normal';
}

function healthClass(health) {
    if (health === 'NORMAL' || health === 'OK')
        return 'apc-health-ok';
    if (health === 'WARNING')
        return 'apc-health-warning';
    if (health === 'REPLACE' || health === 'FAILED')
        return 'apc-health-critical';
    return 'apc-health-unknown';
}

function meter(title, value, percent, fillClass) {
    const wrap = new St.BoxLayout({
        vertical: true,
        style_class: 'apc-meter'
    });

    const head = new St.BoxLayout();
    head.add_child(label(title, 'apc-metric-name'));
    head.add_child(spacer());
    head.add_child(label(value, 'apc-metric-value'));
    wrap.add_child(head);

    const track = new St.BoxLayout({
        style_class: 'apc-track',
        x_expand: true
    });

    const fill = new St.Widget({
        style_class: fillClass
    });

    const updateFill = () => {
        const width = track.get_width();
        if (width > 0)
            fill.set_width(Math.round(width * clamp(percent, 0, 100) / 100));
    };

    track.add_child(fill);
    track.connect('notify::width', updateFill);

    wrap.add_child(track);
    return wrap;
}

function twoColRow(leftActor, rightActor = null) {
    const row = new St.BoxLayout({ style_class: 'apc-info-row' });
    const left = new St.BoxLayout({ style_class: 'apc-info-cell', x_expand: true });
    left.add_child(leftActor);
    row.add_child(left);
    const right = new St.BoxLayout({ style_class: 'apc-info-cell', x_expand: true });
    if (rightActor)
        right.add_child(rightActor);
    row.add_child(right);
    return row;
}

function infoText(text, styleClass = 'apc-muted') {
    return label(text, styleClass);
}

export default class ApcUpsExtension extends Extension {
    enable() {
        this._widget = new St.BoxLayout({ vertical: true, style_class: 'apc-card', reactive: true });
        this._widget.set_position(32, 160);
        Main.layoutManager._backgroundGroup.add_child(this._widget);

        const pos = readJSON(POSITION, null);
        if (pos && Number.isFinite(pos.x) && Number.isFinite(pos.y))
            this._widget.set_position(pos.x, pos.y);

        this._dragging = false;
        this._widget.connect('button-press-event', (_actor, event) => {
            if (event.get_button() !== 1)
                return Clutter.EVENT_PROPAGATE;
            const [x, y] = event.get_coords();
            this._origin = [x, y, this._widget.x, this._widget.y];
            this._dragging = true;
            return Clutter.EVENT_STOP;
        });
        this._widget.connect('motion-event', (_actor, event) => {
            if (!this._dragging)
                return Clutter.EVENT_PROPAGATE;
            const [x, y] = event.get_coords();
            const [startX, startY, oldX, oldY] = this._origin;
            this._widget.set_position(
                Math.max(0, Math.round(oldX + x - startX)),
                Math.max(0, Math.round(oldY + y - startY))
            );
            return Clutter.EVENT_STOP;
        });
        this._widget.connect('button-release-event', () => {
            if (this._dragging)
                this._savePosition();
            this._dragging = false;
            return Clutter.EVENT_STOP;
        });

        this._render();
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 5, () => {
            this._render();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _savePosition() {
        try {
            GLib.mkdir_with_parents(GLib.path_get_dirname(POSITION), 0o700);
            GLib.file_set_contents(POSITION, JSON.stringify({ x: this._widget.x, y: this._widget.y }));
        } catch (e) {
            log(`APC position save: ${e}`);
        }
    }

    _render() {
        if (!this._widget)
            return;
        this._widget.destroy_all_children();

        const data = readJSON(CACHE, { devices: [], updated: null });
        this._widget.add_child(label('⚡ ServRoom · UPS MONITOR', 'apc-title'));

        (data.devices || []).forEach((d, idx) => {
            const host = new St.BoxLayout({ vertical: true, style_class: 'apc-host-block' });
            if (idx > 0)
                host.add_style_class_name('apc-host-separator');

            const header = new St.BoxLayout();
            header.add_child(label(d.label || d.ip, 'apc-hostname'));
            header.add_child(spacer());
            const statusClass = !d.online ? 'apc-offline' : 'apc-online';
            const statusText = !d.online ? 'OFFLINE' : (d.status || 'ONLINE');
            header.add_child(label(`● ${statusText}`, statusClass));
            host.add_child(header);

            if (!d.online) {
                host.add_child(label(`${d.ip} · no SNMP response`, 'apc-error'));
                this._widget.add_child(host);
                return;
            }

            host.add_child(meter('BATTERY', fmt(d.battery, '%'), Number.isFinite(d.battery) ? d.battery : 0,
                (d.battery ?? 0) < 25 ? 'apc-fill-danger' : 'apc-fill'));
            const loadMeter = meter('LOAD', fmt(d.load, '%'),
                Number.isFinite(d.load) ? d.load : 0,
                (d.load ?? 0) > 85 ? 'apc-fill-warning' : 'apc-fill');

            loadMeter.add_style_class_name('apc-load-meter');
            host.add_child(loadMeter);

            host.add_child(twoColRow(
                infoText(`Runtime: ${fmt(d.runtime_min, 'm')}`),
                label(`Temp: ${fmt(d.temperature, '°C')}`, `apc-temperature ${tempClass(d.temperature)}`)
            ));
            host.add_child(twoColRow(
                infoText(`In: ${fmt(d.input_voltage, 'V')}`),
                infoText(`Out: ${fmt(d.output_voltage, 'V')}`)
            ));
            host.add_child(twoColRow(
                label(`Health: ${d.health || 'UNKNOWN'}`, healthClass(d.health)),
                infoText(`Age: ${batteryAgeText(d.battery_age_months)}`)
            ));
            host.add_child(twoColRow(
                infoText(`Replaced: ${d.battery_replace_date || '--'}`),
                label(`Self-test: ${d.selftest || 'UNKNOWN'}`, healthClass(d.selftest))
            ));
            host.add_child(twoColRow(
                infoText(`Last test: ${d.selftest_date || '--'}`),
                null
            ));

            this._widget.add_child(host);
        });

        if (!(data.devices || []).length)
            this._widget.add_child(label('Waiting for SNMP collector...', 'apc-muted'));

        this._widget.add_child(label(`Updated: ${prettyDateTime(data.updated)}`, 'apc-footer'));
    }

    disable() {
        if (this._timer) {
            GLib.Source.remove(this._timer);
            this._timer = null;
        }
        if (this._widget) {
            this._widget.destroy();
            this._widget = null;
        }
    }
}
