"""Read-only dashboard collector. No config, routes or services are changed.

The API calls read_snapshot() and note_contact() after authenticated router
requests. A separate service runs --loop, sampling independently every 15s.
Only the dedicated dashboard runtime and state directories are written.
Values are allowlisted before persistence; WireGuard keys are used solely for
in-memory joins and never serialized. Unknown is different from disconnected.
"""
import argparse
import contextlib
import fcntl
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import time

INTERVAL = 15
STALE_SECONDS = 60
MAX_FILE = 2 * 1024 * 1024
NAME = re.compile(r'^[A-Za-z0-9_.-]{1,64}$')
TOKEN = re.compile(r'^[a-zA-Z0-9_-]{1,40}$')
WG_KEY = re.compile(r'^[A-Za-z0-9+/]{43}=$')
VPNS = frozenset(('mqvpn', 'glorytun_tcp', 'glorytun_udp', 'openvpn', 'wireguard', 'dsvpn', 'softether', 'none'))
PROXIES = frozenset(('none', 'v2ray', 'v2ray-vmess', 'v2ray-socks', 'v2ray-trojan', 'v2ray-vless', 'xray', 'xray-vmess', 'xray-socks', 'xray-trojan', 'xray-shadowsocks', 'xray-vless', 'xray-vless-reality', 'shadowsocks', 'shadowsocks-go', 'shadowsocks-rust'))
SERVICES = ('omr-admin.service', 'omr-dashboard-collector.service', 'mqvpn.service', 'glorytun-tcp@tun0.service', 'glorytun-udp@tun0.service', 'openvpn@tun0.service', 'xray.service', 'v2ray.service', 'shadowsocks-go.service', 'wg-quick@client-wg0.service')


def _read(path):
    try:
        with open(path, 'rb') as f:
            raw = f.read(MAX_FILE + 1)
        return raw.decode('utf-8') if len(raw) <= MAX_FILE else None
    except (OSError, UnicodeError):
        return None


def _json(path):
    text = _read(path)
    try:
        return json.loads(re.sub(r',\s*}', '}', text)) if text is not None else None
    except (ValueError, TypeError):
        return None


def _token(value):
    return value if isinstance(value, str) and TOKEN.fullmatch(value) else None


def _ip(value, network=False):
    try:
        return str(ipaddress.ip_network(value, strict=False) if network else ipaddress.ip_address(value))
    except (ValueError, TypeError):
        return None


def _port(value):
    if isinstance(value, str) and value.isascii() and value.isdigit() and len(value) <= 5: value = int(value)
    return value if type(value) is int and 0 < value < 65536 else None


def _contains(elements, address):
    """Read nft JSON singleton, prefix, interval and wrapped elements."""
    try:
        wanted = ipaddress.ip_address(address)
        for item in elements:
            if isinstance(item, str):
                if wanted in ipaddress.ip_network(item, strict=False): return True
            elif isinstance(item, dict) and 'elem' in item:
                value = item['elem']
                if isinstance(value, dict) and 'val' in value: value = value['val']
                result = _contains([value], address)
                if result is None: return None
                if result: return True
            elif isinstance(item, dict) and 'prefix' in item:
                value = item['prefix']
                if wanted in ipaddress.ip_network(str(value['addr']) + '/' + str(value['len']), strict=False): return True
            elif isinstance(item, dict) and 'range' in item:
                first, last = item['range']
                if ipaddress.ip_address(first) <= wanted <= ipaddress.ip_address(last): return True
            else:
                return None
        return False
    except (ValueError, TypeError, KeyError):
        return None


def _atomic(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.dashboard-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, separators=(',', ':'), allow_nan=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextlib.contextmanager
def _lock(root, nonblocking=False):
    directory = root / 'var/lib/omr-dashboard'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(str(directory / 'state.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | (fcntl.LOCK_NB if nonblocking else 0))
        yield
    finally:
        os.close(fd)


def note_contact(username, route=None, timestamp=None, root='/', clock=time.time):
    """Record authenticated API contact, not proof that a tunnel is up.

    Route and request contents are deliberately discarded. Lock contention
    drops this optional observation rather than delaying an API request.
    """
    if not isinstance(username, str) or not NAME.fullmatch(username):
        return False
    try:
        now = int(clock())
        when = now if timestamp is None else int(timestamp)
        if when < 0 or when > now + 60:
            return False
        root = Path(root)
        with _lock(root, nonblocking=True):
            path = root / 'var/lib/omr-dashboard/history.json'
            history = _json(path) or {}
            if not isinstance(history, dict): history = {}
            contacts = history.get('contacts')
            if not isinstance(contacts, dict): contacts = {}
            contacts = {k: v for k, v in contacts.items() if isinstance(k, str) and NAME.fullmatch(k) and type(v) is int and 0 <= v <= now + 60}
            if username not in contacts and len(contacts) >= 1024:
                contacts.pop(min(contacts, key=contacts.get))
            contacts[username] = max(when, contacts.get(username, 0))
            history['contacts'] = contacts
            _atomic(path, history)
        return True
    except (OSError, ValueError, TypeError, OverflowError):
        return False


def _empty(now, warning):
    return {'schema_version': 1, 'generated_at': None, 'collection_state': 'unavailable', 'server': {}, 'clients': None,
            'wireguard': {'interface': 'client-wg0', 'state': 'unknown', 'peers': None, 'summary': {}},
            'services': [], 'events': [], 'warnings': [warning]}


def read_snapshot(root='/', clock=time.time):
    """Read cached snapshot only; never execute commands or contact services."""
    now = int(clock())
    data = _json(Path(root) / 'run/omr-dashboard/snapshot.json')
    if (not isinstance(data, dict) or data.get('schema_version') != 1 or type(data.get('generated_at')) is not int
            or not isinstance(data.get('server'), dict) or not isinstance(data.get('clients'), list)
            or not isinstance(data.get('wireguard'), dict) or not isinstance(data['wireguard'].get('peers'), list)
            or not isinstance(data.get('services'), list) or not isinstance(data.get('events'), list)
            or not isinstance(data.get('warnings'), list)):
        return _empty(now, 'collector snapshot unavailable')
    if now - data['generated_at'] > STALE_SECONDS or data['generated_at'] > now + 60:
        data.setdefault('warnings', []).append('collector snapshot stale')
    return data


class Collector:
    def __init__(self, root='/', runner=subprocess.run, clock=time.time, control=None):
        self.root, self.runner, self.clock = Path(root), runner, clock
        self.control = control
        self.deadline = None

    def path(self, value):
        return self.root / value.lstrip('/')

    def command(self, argv):
        try:
            remaining = self.deadline - time.monotonic() if self.deadline is not None else 1
            if remaining <= 0: return None
            result = self.runner(argv, text=True, capture_output=True, check=False, timeout=min(1, remaining))
            # systemctl uses nonzero exit status for a known inactive unit.
            ok = result.returncode == 0 or (argv[0] == 'systemctl' and result.returncode in (3, 4))
            return result.stdout if ok and len(result.stdout) <= MAX_FILE else None
        except (OSError, subprocess.SubprocessError):
            return None

    def mq_status(self, config):
        if self.control is not None:
            try: return self.control()
            except (OSError, ValueError, TypeError): return None
        if self.root != Path('/') or not isinstance(config, dict): return None
        listen = config.get('control_listen', '127.0.0.1:9090')
        if not isinstance(listen, str): return None
        host, sep, port = listen.rpartition(':')
        host = host.strip('[]')
        if host in ('0.0.0.0', '*', 'localhost'): host = '127.0.0.1'
        if host == '::': host = '::1'
        if not sep or host not in ('127.0.0.1', '::1') or _port(port) is None: return None
        try:
            deadline = time.monotonic() + 1
            with socket.create_connection((host, int(port)), timeout=1) as conn:
                conn.sendall(b'{"cmd":"get_status"}\n')
                result = bytearray()
                while b'\n' not in result and len(result) <= 65536:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0: return None
                    conn.settimeout(remaining)
                    part = conn.recv(4096)
                    if not part: return None
                    result.extend(part)
            if len(result) > 65536: return None
            return json.loads(result.split(b'\n', 1)[0])
        except (OSError, ValueError): return None

    def sys(self, path):
        text = _read(self.path(path))
        return text.strip() if text is not None else None

    def sample(self):
        self.deadline = time.monotonic() + 8
        now = int(self.clock())
        config = _json(self.path('/etc/openmptcprouter-vps-admin/omr-admin-config.json'))
        warnings = []
        if not isinstance(config, dict): config = {}; warnings.append('OMR configuration unavailable')
        users = config.get('users')
        users = users[0] if isinstance(users, list) and users and isinstance(users[0], dict) else {}
        mq = _json(self.path('/etc/mqvpn/server.json'))
        mq = mq if isinstance(mq, dict) else {}
        status = self.mq_status(mq)
        live = None
        if isinstance(status, dict) and status.get('ok') is True and isinstance(status.get('clients'), list):
            live = {c['user']: c for c in status['clients'][:1024] if isinstance(c, dict) and isinstance(c.get('user'), str) and NAME.fullmatch(c['user'])}
        mq_users = {u.get('name') for u in mq.get('users', []) if isinstance(u, dict) and isinstance(u.get('name'), str)} if isinstance(mq.get('users', []), list) else set()
        mq_settings = {}
        choices = {'scheduler': ('wlb', 'wlb_udp_pin', 'minrtt', 'wrtt', 'wrr', 'backup', 'backup_fec', 'rap', 'redundant'), 'cc': ('bbr2', 'bbr', 'cubic'), 'fec_scheme': ('galois_calculation', 'packet_mask', 'reed_solomon', 'xor'), 'reinjection_mode': ('default', 'deadline', 'dgram')}
        for key, values in choices.items():
            if isinstance(mq.get(key), str) and mq[key] in values: mq_settings[key] = mq[key]
        for key in ('fec_enable', 'reinjection_control', 'sync_path_labels', 'push_path_labels'):
            if type(mq.get(key)) is bool: mq_settings[key] = mq[key]
        for key in ('reinjection_srtt_factor_pct', 'reinjection_hard_deadline_ms', 'reinjection_deadline_lower_bound_ms', 'init_max_path_id', 'max_clients'):
            if type(mq.get(key)) is int and 0 <= mq[key] <= 1048576: mq_settings[key] = mq[key]
        listen = mq.get('listen')
        if isinstance(listen, str):
            port = listen.rpartition(':')[2]
            if _port(port) is not None: mq_settings['listen_port'] = _port(port)
        reorder = mq.get('reorder')
        if isinstance(reorder, dict):
            safe_reorder = {}
            if type(reorder.get('enabled')) is bool or reorder.get('enabled') in ('on', 'off', 'auto'): safe_reorder['enabled'] = reorder['enabled']
            for key in ('max_wait_ms', 'cap_packets'):
                value = reorder.get(key)
                if type(value) is int and 0 <= value <= 1048576: safe_reorder[key] = value
            if safe_reorder: mq_settings['reorder'] = safe_reorder
        scheduler = _token(self.sys('/proc/sys/net/mptcp/scheduler')) or _token(self.sys('/proc/sys/net/mptcp/mptcp_scheduler'))
        cc = _token(self.sys('/proc/sys/net/ipv4/tcp_congestion_control'))
        def tokens(path):
            raw = self.sys(path)
            return [x for x in raw.split() if _token(x)] if raw is not None else None
        gate_path = self.path('/etc/openmptcprouter-vps-admin/wg-remote-lan-access.enabled')
        gate_value = self.sys('/etc/openmptcprouter-vps-admin/wg-remote-lan-access.enabled')
        gate = False if not gate_path.exists() else (True if gate_value == 'allow' else None)
        wg = self.wireguard(now, gate)
        interfaces = self.interfaces()
        routes = self.routes()
        tcp = self.tcp_connections()
        owners = {}
        for uname, info in users.items():
            if not isinstance(uname, str) or not NAME.fullmatch(uname) or not isinstance(info, dict): continue
            for field in ('vpn_port', 'shadowsocks_port'):
                port = _port(info.get(field))
                if port is not None: owners.setdefault(port, set()).add((uname, field))
        profile = _json(self.path('/var/lib/omr-profiles/transaction.json'))
        profile_state = profile.get('state') if isinstance(profile, dict) else None
        if profile_state not in ('preparing', 'applying', 'pending', 'confirmed', 'rolled_back', 'rollback_failed'): profile_state = None
        services = self.services()
        service_states = {s['name']: s['state'] for s in services}
        clients = []
        for name, user in sorted(users.items())[:1024]:
            if not isinstance(name, str) or not NAME.fullmatch(name) or not isinstance(user, dict): continue
            if user.get('permissions') == 'admin' and name != 'openmptcprouter' and not any(k in user for k in ('userid', 'vpn', 'vpnremoteip')): continue
            raw_vpn, raw_proxy = user.get('vpn'), user.get('proxy')
            vpn = raw_vpn if isinstance(raw_vpn, str) and raw_vpn in VPNS else None
            proxy = raw_proxy if isinstance(raw_proxy, str) and raw_proxy in PROXIES else None
            connected = (name in live) if vpn == 'mqvpn' and live is not None else None
            nets = user.get('lanips', [])
            nets = sorted(set(filter(None, (_ip(x, True) for x in nets[:128])))) if isinstance(nets, list) else []
            policy = []
            for entry in (mq.get('path_policy', [])[:4096] if isinstance(mq.get('path_policy', []), list) else []):
                if not isinstance(entry, dict) or entry.get('user') != name: continue
                iface = _token(entry.get('iface'))
                if not iface: continue
                item = {'interface': iface}
                for field in ('weight', 'dscp_mask'):
                    value = entry.get(field)
                    if type(value) is int and 0 <= value <= 65535: item[field] = value
                policy.append(item)
                if len(policy) >= 128: break
            paths = []
            session = live.get(name) if live is not None else None
            raw_paths = session.get('paths') if isinstance(session, dict) else None
            if isinstance(raw_paths, list):
                for path in raw_paths[:128]:
                    if not isinstance(path, dict): continue
                    item = {'source': 'mqvpn get_status'}
                    for field in ('path_id', 'srtt_ms', 'min_rtt_ms', 'cwnd', 'in_flight', 'bytes_tx', 'bytes_rx', 'pkt_sent', 'pkt_recv', 'pkt_lost', 'state', 'reinject_tx_bytes'):
                        value = path.get(field)
                        if type(value) is int and 0 <= value < 2**64: item[field] = value
                    label = path.get('state_label')
                    if label in ('init', 'validating', 'active', 'closing', 'closed', 'unknown'): item['state_label'] = label
                    if len(item) > 1: paths.append(item)
            configured_tun = mq.get('tun_name') if vpn == 'mqvpn' else 'tun0' if vpn in ('glorytun_tcp', 'glorytun_udp', 'openvpn') else None
            if not isinstance(configured_tun, str) or not re.fullmatch(r'(?:mqvpn[0-9]*|tun[0-9]+)', configured_tun): configured_tun = None
            remote_address = _ip(user.get('vpnremoteip'))
            route_interface = None
            if remote_address and routes is not None:
                address = ipaddress.ip_address(remote_address)
                matches = [(net.prefixlen, dev) for net, dev in routes if address.version == net.version and address in net]
                if matches:
                    longest = max(prefix for prefix, _ in matches)
                    devices = {dev for prefix, dev in matches if prefix == longest}
                    dev = next(iter(devices)) if len(devices) == 1 else ''
                    if (vpn == 'mqvpn' and dev.startswith('mqvpn')) or (vpn in ('glorytun_tcp', 'glorytun_udp', 'openvpn') and dev.startswith('tun')):
                        route_interface = dev
            if configured_tun is None and route_interface: configured_tun = route_interface
            iface = interfaces.get(configured_tun) if configured_tun else None
            tunnel_settings = dict(mq_settings) if vpn == 'mqvpn' else {}
            if policy: tunnel_settings['path_policy'] = policy
            service_map = {'mqvpn': 'mqvpn.service', 'glorytun_tcp': 'glorytun-tcp@tun0.service', 'openvpn': 'openvpn@tun0.service', 'xray': 'xray.service', 'v2ray': 'v2ray.service', 'shadowsocks-go': 'shadowsocks-go.service'}
            proxy_service = service_map.get(proxy.split('-')[0]) if proxy else None
            if proxy == 'shadowsocks-go': proxy_service = 'shadowsocks-go.service'
            settings = {'mqvpn_user_configured': name in mq_users if mq else None, 'profile_state': profile_state if name == 'openmptcprouter' else None}
            for field in ('vpnlocalip', 'ula'):
                value = _ip(user.get(field)) or _ip(user.get(field), True)
                if value: settings[field] = value
            for field in ('shadowsocks_port', 'vpn_port'):
                value = _port(user.get(field))
                if value is not None: settings[field] = value
            def observed_port(field, applicable):
                port = _port(user.get(field))
                return tcp.get(port, 0) if applicable and tcp is not None and port is not None and owners.get(port) == {(name, field)} else None
            vpn_tcp = observed_port('vpn_port', vpn == 'glorytun_tcp')
            proxy_tcp = observed_port('shadowsocks_port', proxy in ('shadowsocks', 'shadowsocks-go', 'shadowsocks-rust'))
            clients.append({'id': name, 'username': name, 'state': 'connected' if connected is True else 'disconnected' if connected is False else 'unknown',
                'last_seen_at': None, 'last_connected_at': None, 'last_disconnected_at': None,
                'tunnel': {'configured': vpn, 'observed': 'mqvpn' if connected else None, 'interface': configured_tun if iface else None, 'address': remote_address, 'route_interface': route_interface, 'route_source': 'main routing table; policy routing not evaluated' if routes is not None else 'unavailable', 'interface_addresses': iface['addresses'] if iface else [], 'interface_state': iface['state'] if iface else 'unknown', 'interface_counters': iface['counters'] if iface else {}, 'interface_source': 'ip -s -j address show; aggregate for interface' if iface else 'unavailable', 'state': 'connected' if connected is True else 'disconnected' if connected is False else 'unknown', 'scheduler': mq_settings.get('scheduler') if vpn == 'mqvpn' else None, 'cc': mq_settings.get('cc') if vpn == 'mqvpn' else None, 'mtu': iface['mtu'] if iface else None, 'paths': paths, 'settings': tunnel_settings, 'source': 'mqvpn get_status' if connected is not None else 'unavailable', 'service_state': service_states.get(service_map.get(vpn), 'unknown'), 'tcp_connections': vpn_tcp, 'tcp_source': 'ss unique configured port; authentication not verified' if vpn_tcp is not None else 'unavailable or ambiguous'},
                'proxy': {'configured': proxy, 'observed': None, 'state': 'unknown', 'service_state': service_states.get(proxy_service, 'unknown'), 'tcp_connections': proxy_tcp, 'source': 'ss unique configured port; authentication not verified' if proxy_tcp is not None else 'service state is not per-user proxy activity'},
                'mptcp': {'scheduler': scheduler, 'cc': cc, 'settings': {}, 'source': 'VPS kernel defaults; router settings unavailable'},
                'lan_subnets': nets, 'rth': {'enabled': wg['summary']['interface_present'] if name == 'openmptcprouter' else None, 'lan_access_requested': gate if name == 'openmptcprouter' else None, 'lan_access_effective': wg['summary']['lan_firewall_open'] if name == 'openmptcprouter' else None, 'source': 'WireGuard interface and nft LAN set; reachability not verified'}, 'settings': settings})
        server = self.server(scheduler, cc, tokens)
        return {'schema_version': 1, 'generated_at': now, 'server': server, 'clients': clients, 'wireguard': wg, 'services': services, 'events': [], 'warnings': warnings}

    def services(self):
        output = self.command(['systemctl', 'is-active'] + list(SERVICES))
        lines = output.splitlines() if output is not None else []
        allowed = ('active', 'inactive', 'failed', 'activating', 'deactivating')
        return [{'name': name, 'state': lines[i].strip() if i < len(lines) and lines[i].strip() in allowed else 'unknown', 'source': 'systemctl'} for i, name in enumerate(SERVICES)]

    def tcp_connections(self):
        text = self.command(['ss', '-Hnt', 'state', 'established'])
        if text is None: return None
        counts = {}
        for line in text.splitlines()[:65536]:
            fields = line.split()
            if len(fields) < 4: return None
            local = fields[2].rpartition(':')[2]
            port = _port(local)
            if port is None: return None
            counts[port] = counts.get(port, 0) + 1
        return counts

    def interfaces(self):
        output = self.command(['ip', '-s', '-j', 'address', 'show'])
        try: rows = json.loads(output)
        except (ValueError, TypeError): return {}
        if not isinstance(rows, list): return {}
        result = {}
        for row in rows[:1024]:
            if not isinstance(row, dict): continue
            name = row.get('ifname')
            if not isinstance(name, str) or not re.fullmatch(r'(?:mqvpn[0-9]*|tun[0-9]+)', name): continue
            mtu = row.get('mtu')
            mtu = mtu if type(mtu) is int and 0 < mtu <= 65535 else None
            state = row.get('operstate')
            state = state.lower() if isinstance(state, str) and state.lower() in ('up', 'down', 'unknown', 'dormant', 'lowerlayerdown') else 'unknown'
            addresses = []
            addr_info = row.get('addr_info')
            for entry in addr_info[:128] if isinstance(addr_info, list) else []:
                if isinstance(entry, dict):
                    addr = _ip(entry.get('local'))
                    if addr: addresses.append(addr)
            counters = {}
            stats = row.get('stats64', row.get('stats'))
            if isinstance(stats, dict):
                for direction in ('rx', 'tx'):
                    values = stats.get(direction)
                    if not isinstance(values, dict): continue
                    for field in ('bytes', 'packets', 'errors', 'dropped'):
                        value = values.get(field)
                        if type(value) is int and 0 <= value < 2**64: counters[direction + '_' + field] = value
            result[name] = {'mtu': mtu, 'state': state, 'addresses': addresses, 'counters': counters}
        return result

    def routes(self):
        output = self.command(['ip', '-j', '-4', 'route', 'show', 'table', 'main'])
        try: rows = json.loads(output)
        except (ValueError, TypeError): return None
        if not isinstance(rows, list): return None
        result = []
        for row in rows[:4096]:
            if not isinstance(row, dict): continue
            dev, dst = row.get('dev'), row.get('dst')
            if not isinstance(dev, str) or not re.fullmatch(r'(?:mqvpn[0-9]*|tun[0-9]+)', dev): continue
            try:
                net = ipaddress.ip_network(dst, strict=False)
                if net.prefixlen > 0: result.append((net, dev))
            except (ValueError, TypeError): pass
        return result

    def server(self, scheduler, cc, tokens):
        version = None
        for file in ('/etc/motd.head', '/etc/motd'):
            found = re.search(r'OpenMPTCProuter VPS\s+(\d[A-Za-z0-9_.+-]{0,39})', self.sys(file) or '')
            if found: version = found.group(1); break
        uptime = self.sys('/proc/uptime')
        try: uptime = int(float(uptime.split()[0])) if uptime else None
        except (ValueError, OverflowError): uptime = None
        load = self.sys('/proc/loadavg')
        try:
            load = [float(x) for x in load.split()[:3]] if load else None
            if load is not None and (len(load) != 3 or not all(math.isfinite(x) and x >= 0 for x in load)): load = None
        except ValueError: load = None
        mem = {}
        for line in (self.sys('/proc/meminfo') or '').splitlines():
            m = re.fullmatch(r'(MemTotal|MemAvailable):\s+(\d+)\s+kB', line)
            if m: mem[m.group(1)] = int(m.group(2)) * 1024
        kernel = self.sys('/proc/sys/kernel/osrelease')
        hostname = self.sys('/proc/sys/kernel/hostname')
        total, available = mem.get('MemTotal'), mem.get('MemAvailable')
        used = total - available if total is not None and available is not None and available <= total else None
        return {'version': version, 'kernel': kernel if kernel and re.fullmatch(r'[A-Za-z0-9_.+~-]{1,128}', kernel) else None, 'hostname': hostname if hostname and re.fullmatch(r'[A-Za-z0-9_.-]{1,253}', hostname) else None, 'uptime_seconds': uptime, 'load': load, 'memory': {'total_bytes': total, 'available_bytes': available, 'used_bytes': used, 'source': 'procfs MemTotal minus MemAvailable'}, 'mptcp': {'scheduler': scheduler, 'cc': cc, 'available_schedulers': tokens('/proc/sys/net/mptcp/available_schedulers'), 'available_cc': tokens('/proc/sys/net/ipv4/tcp_available_congestion_control'), 'source': 'procfs'}}

    def wireguard(self, now, gate):
        registry = _json(self.path('/etc/openmptcprouter-vps-admin/wg-remote-manager/peers.json'))
        records = registry.get('peers') if isinstance(registry, dict) and registry.get('version') == 1 else None
        records = records if isinstance(records, list) else []
        def wg(field):
            text = self.command(['wg', 'show', 'client-wg0', field])
            if text is None: return None
            rows = {}
            for line in text.splitlines():
                parts = line.split()
                if len(parts) >= 2 and WG_KEY.fullmatch(parts[0]): rows[parts[0]] = parts[1:]
            return rows
        allowed, handshakes, transfer = wg('allowed-ips'), wg('latest-handshakes'), wg('transfer')
        def nft_set(name):
            text = self.command(['nft', '-j', 'list', 'set', 'inet', 'omr', name])
            try:
                data = json.loads(text)
                value = next(x['set'].get('elem', []) for x in data['nftables'] if x.get('set', {}).get('name') == name)
                return value if isinstance(value, list) else None
            except (ValueError, TypeError, KeyError, StopIteration, AttributeError): return None
        peer_set, lan_set = nft_set('wg_remote_peer_lan_v4'), nft_set('wg_remote_lan_v4')
        peers = []
        for p in records[:1024]:
            if not isinstance(p, dict): continue
            name, key, addr, state, lan = p.get('name'), p.get('public_key'), _ip(p.get('ip')), p.get('state'), p.get('lan')
            if not isinstance(name, str) or not NAME.fullmatch(name) or not isinstance(key, str) or not WG_KEY.fullmatch(key) or not addr or state not in ('active', 'disabled', 'adding', 'disabling', 'removing', 'quarantine') or type(lan) is not bool: continue
            h = handshakes.get(key, [None])[0] if handshakes is not None else None
            h = int(h) if isinstance(h, str) and h.isascii() and h.isdigit() and len(h) <= 20 and 0 < int(h) <= now + 60 else None
            values = transfer.get(key, []) if transfer is not None else []
            counts = [int(v) if isinstance(v, str) and v.isascii() and v.isdigit() and len(v) <= 20 else None for v in values[:2]]
            counts += [None] * (2 - len(counts))
            present = (key in allowed) if allowed is not None else None
            match = _contains(peer_set, addr) if peer_set is not None else None
            lan_valid = _contains(lan_set, '0.0.0.0') if lan_set is not None else None
            effective = bool(match and lan_set) if match is not None and lan_valid is not None else None
            peers.append({'id': name, 'name': name, 'address': addr, 'enabled': state == 'active', 'connected': (h is not None and now - h <= 240) if handshakes is not None and present is not None else None, 'last_handshake_at': h, 'rx_bytes': counts[0], 'tx_bytes': counts[1], 'lan_access_requested': lan, 'lan_access_effective': effective, 'state': state, 'source': 'wireguard handshake; nft sets'})
        lan_valid = _contains(lan_set, '0.0.0.0') if lan_set is not None else None
        lan_open = bool(lan_set) if lan_valid is not None else None
        return {'interface': 'client-wg0', 'state': 'available' if allowed is not None else 'unknown', 'peers': peers, 'summary': {'global_lan_gate': gate, 'interface_present': True if allowed is not None else None, 'lan_firewall_open': lan_open, 'peer_count': len(peers), 'source': 'registry, WireGuard and nft sets; recent handshake <= 240 seconds; reachability not verified'}}

    def collect(self):
        data = self.sample()
        now = data['generated_at']
        with _lock(self.root):
            path = self.path('/var/lib/omr-dashboard/history.json')
            history = _json(path) or {}
            if not isinstance(history, dict): history = {}
            contacts = history.get('contacts') if isinstance(history.get('contacts'), dict) else {}
            previous = history.get('clients') if isinstance(history.get('clients'), dict) else {}
            events = history.get('events') if isinstance(history.get('events'), list) else []
            events = [e for e in events if isinstance(e, dict) and set(e) in ({'at', 'username', 'state'}, {'at', 'username', 'state', 'after_observation_gap'}) and type(e['at']) is int and isinstance(e['username'], str) and NAME.fullmatch(e['username']) and e['state'] in ('connected', 'disconnected') and ('after_observation_gap' not in e or type(e['after_observation_gap']) is bool)][-100:]
            current = {}
            for client in data['clients']:
                name, state = client['username'], client['state']
                old = previous.get(name) if isinstance(previous.get(name), dict) else {}
                prior = old.get('state') if old.get('state') in ('connected', 'disconnected') else None
                last_up = old.get('last_connected_at') if type(old.get('last_connected_at')) is int else None
                last_down = old.get('last_disconnected_at') if type(old.get('last_disconnected_at')) is int else None
                prior_sample = old.get('last_observed_at')
                gap = old.get('observation_gap') is True or (type(prior_sample) is int and (now - prior_sample > INTERVAL * 3 or now < prior_sample))
                transition_gap = old.get('last_transition_after_gap') is True
                if state in ('connected', 'disconnected') and state != prior:
                    if state == 'connected': last_up = now
                    elif prior == 'connected': last_down = now
                    if state == 'connected' or prior == 'connected':
                        events.append({'at': now, 'username': name, 'state': state, 'after_observation_gap': gap})
                        transition_gap = gap
                seen = contacts.get(name)
                client['last_seen_at'] = seen if type(seen) is int and 0 <= seen <= now + 60 else None
                client['last_connected_at'], client['last_disconnected_at'] = last_up, last_down
                client['last_transition_after_gap'] = transition_gap
                client['history_source'] = 'first observed transition; timestamps after telemetry gaps are not exact disconnect times'
                current[name] = {'state': state if state != 'unknown' else prior, 'last_connected_at': last_up, 'last_disconnected_at': last_down, 'observation_gap': state == 'unknown', 'last_observed_at': now, 'last_transition_after_gap': transition_gap}
            contacts = {k: v for k, v in contacts.items() if k in current and type(v) is int and 0 <= v <= now + 60}
            history = {'contacts': contacts, 'clients': current, 'events': events[-100:]}
            data['events'] = history['events']
            _atomic(path, history)
            _atomic(self.path('/run/omr-dashboard/snapshot.json'), data)
        return data


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--once', action='store_true')
    group.add_argument('--loop', action='store_true')
    args = parser.parse_args()
    collector = Collector()
    while True:
        started = time.monotonic()
        try: collector.collect()
        except (OSError, ValueError, TypeError): pass
        if args.once: break
        time.sleep(max(0, INTERVAL - (time.monotonic() - started)))


if __name__ == '__main__':
    main()
