"""Transactional, credential-free VPS profile changes for OMR 3K.

The journal contains only the allowlisted values being changed, never a copy of
server.json. The runtime adapter is replaceable for isolated tests. A pending
operation is rolled back on timeout or on a restarted API after a partial apply.
"""
import contextlib
import copy
import fcntl
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import tempfile
import threading
import time

TRANSACTION_RE = re.compile(r'^[0-9a-f]{32}$')
TCP_CC = ('reno', 'cubic', 'bbr', 'bbr1', 'bbr2', 'nanqinlang') + tuple(
    f'nanbbr{family}_{kind}' for family in ('1', '2', '3')
    for kind in ('light', 'def', 'aggr', 'var'))
MQ_CC = ('bbr2', 'bbr', 'cubic')  # Other XQUIC CCs can silently compile-fallback.
MQ_SCHEDULERS = ('wlb', 'wlb_udp_pin', 'minrtt', 'wrtt', 'wrr', 'backup',
                 'backup_fec', 'rap', 'redundant')
FEC_SCHEMES = ('galois_calculation', 'packet_mask', 'reed_solomon', 'xor')
# Frozen 0.1163-3K provenance records FEC, XOR, RSC and PKM for this exact
# package. Other package builds may advertise generic FEC while omitting a
# scheme: get_build_info does not expose enough detail to claim them supported.
VERIFIED_FEC_BINARIES = {
    '0.16.2-3k2': '4e9eb2d799b19f8ca27e8e675f101cc16d8e5ac3b8b291ba9e8e58222135cf6e',
}
MQ_DEFAULTS = {'scheduler': 'wlb', 'cc': 'bbr2', 'fec_enable': False,
               'fec_scheme': 'xor', 'reinjection_control': False,
               'reinjection_mode': 'default',
               'reorder': {'enabled': 'off', 'max_wait_ms': 30, 'cap_packets': 1024}}
MQ_FIELDS = frozenset(MQ_DEFAULTS) - {'reorder'}
REORDER_FIELDS = frozenset(MQ_DEFAULTS['reorder'])
MPTCP_DEPENDENTS = ('shadowsocks-libev-manager@manager.service', 'shadowsocks-go.service',
                    'v2ray.service', 'xray.service', 'glorytun-tcp@tun0.service',
                    'openvpn@tun0.service')


class ProfileError(Exception):
    def __init__(self, status, detail):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _atomic_bytes(filename, data, mode, owner=None):
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.omr-profile-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, mode)
        if owner is not None and owner != (os.geteuid(), os.getegid()):
            # Preserve an existing service file owner or fail before replacing it.
            os.chown(temp, *owner)
        os.replace(temp, path)
        directory = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        try:
            os.unlink(temp)
        except FileNotFoundError:
            pass


def _read_json(path):
    with open(path, encoding='utf-8') as stream:
        result = json.load(stream)
    if not isinstance(result, dict):
        raise RuntimeError('Invalid configuration format')
    return result


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path, data, default_mode=0o600):
    try:
        info = os.stat(path)
        mode = stat.S_IMODE(info.st_mode)
        owner = (info.st_uid, info.st_gid)
    except FileNotFoundError:
        mode = default_mode
        owner = None
    _atomic_bytes(path, (json.dumps(data, indent=2, sort_keys=True) + '\n').encode(), mode, owner)


def _sysctl(name, value=None):
    command = ['sysctl', '-n', name] if value is None else ['sysctl', '-qw', name + '=' + str(value)]
    return subprocess.run(command, check=True, capture_output=True, text=True, timeout=8).stdout.strip()


def load_tcp_cc(name):
    if name not in TCP_CC:
        raise RuntimeError('Unsupported TCP congestion control')
    # The API unit has no CAP_SYS_MODULE. The instance unit is run by systemd
    # and receives a prevalidated, allowlisted module name as one argument.
    subprocess.run(['systemctl', 'start', 'omr-profile-load-cc@' + name + '.service'],
                   check=True, capture_output=True, timeout=20)


def ensure_system_nanbbr(cc):
    if cc not in ('nanbbr1_var', 'nanbbr2_var', 'nanbbr3_var'):
        raise RuntimeError('Unsupported NanBBR parameter')
    parameter = '/sys/module/tcp_' + cc + '/parameters/aggressiveness'
    if not os.path.isfile(parameter):
        load_tcp_cc(cc)
    if not os.path.isfile(parameter) or not os.access(parameter, os.W_OK):
        raise RuntimeError('NanBBR aggression parameter is unavailable')
    return parameter


def watchdog_control(command, mq_config='/etc/mqvpn/server.json'):
    config = _read_json(mq_config)
    listen = config.get('control_listen', '127.0.0.1:9090')
    if not isinstance(listen, str): raise RuntimeError('MQVPN control address is invalid')
    host, sep, port = listen.rpartition(':')
    host = host.strip('[]')
    if host in ('0.0.0.0', '*'): host = '127.0.0.1'
    if host == '::': host = '::1'
    if host not in ('127.0.0.1', '::1', 'localhost') or not sep or not port.isdigit() or not 0 < int(port) < 65536:
        raise RuntimeError('MQVPN control must listen locally for profile recovery')
    with socket.create_connection((host, int(port)), timeout=5) as stream:
        stream.sendall((json.dumps(command) + '\n').encode())
        response = b''
        while b'\n' not in response and len(response) < 65536:
            chunk = stream.recv(4096)
            if not chunk: break
            response += chunk
    try:
        obj = json.loads(response)
        return obj if isinstance(obj, dict) else {'ok': False}
    except (ValueError, UnicodeError):
        return {'ok': False}


def watchdog_read_nanbbr(filename='/etc/openmptcprouter-vps-admin/nanbbr-var.json'):
    try:
        value = _read_json(filename).get('aggressiveness')
        if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 100:
            return value
    except (OSError, ValueError, RuntimeError):
        pass
    return None


def _scheduler_key():
    for name in ('net.mptcp.scheduler', 'net.mptcp.mptcp_scheduler'):
        if Path('/proc/sys/' + name.replace('.', '/')).exists():
            return name
    raise RuntimeError('MPTCP scheduler is unavailable')


def _restore_scheduler(name):
    key = _scheduler_key()
    try:
        _sysctl(key, name)
    except subprocess.SubprocessError:
        # After a reboot the previous BPF scheduler may not have been
        # registered yet. Retry only an existing object with a safe basename.
        if not re.fullmatch(r'bpf_[a-z0-9_]{1,32}', name): raise
        obj = Path('/usr/share/bpf/scheduler') / ('mptcp_' + name + '.o')
        if not obj.is_file(): raise
        os.makedirs('/sys/fs/bpf/mptcp', exist_ok=True)
        result = subprocess.run(['bpftool', 'struct_ops', 'register', str(obj), '/sys/fs/bpf/mptcp'],
                                capture_output=True, text=True, timeout=15, check=False)
        if result.returncode and 'File exists' not in (result.stderr or ''):
            raise RuntimeError('Previous MPTCP scheduler could not be registered')
        _sysctl(key, name)
    if _sysctl(key) != name:
        raise RuntimeError('MPTCP scheduler readback mismatch')


def _restart_mptcp_dependents():
    # Affect only units that were already active; ordinary unrelated services
    # and disabled VPNs must never be started by a profile change.
    for unit in MPTCP_DEPENDENTS:
        active = subprocess.run(['systemctl', 'is-active', '--quiet', unit],
                                check=False, capture_output=True, timeout=8)
        if active.returncode == 0:
            subprocess.run(['systemctl', 'restart', unit], check=True,
                           capture_output=True, timeout=30)
            subprocess.run(['systemctl', 'is-active', '--quiet', unit], check=True,
                           capture_output=True, timeout=8)
        elif active.returncode not in (3, 4):
            raise RuntimeError('Could not determine MPTCP service status')


def _boot_time():
    # Includes suspend time on Linux, so sleeping cannot extend a rollback.
    return time.clock_gettime(getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC))


def _boot_id():
    value = Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip()
    if not re.fullmatch(r'[0-9a-f-]{36}', value):
        raise RuntimeError('Cannot establish VPS boot identity')
    return value


def _mq_settings(config):
    result = {key: copy.deepcopy(config.get(key, default))
              for key, default in MQ_DEFAULTS.items() if key != 'reorder'}
    configured = config.get('reorder') or {}
    if not isinstance(configured, dict):
        raise RuntimeError('MQVPN reorder configuration is invalid')
    result['reorder'] = {key: configured.get(key, default)
                         for key, default in MQ_DEFAULTS['reorder'].items()}
    for key in ('scheduler', 'cc', 'fec_scheme', 'reinjection_mode'):
        if not isinstance(result[key], str) or not re.fullmatch(r'[a-z0-9_]{1,40}', result[key]):
            raise ProfileError(409, 'MQVPN profile settings have an invalid format')
    for key in ('fec_enable', 'reinjection_control'):
        if not isinstance(result[key], bool):
            raise ProfileError(409, 'MQVPN profile settings have an invalid format')
    if result['reorder']['enabled'] not in ('on', 'off', 'auto'):
        raise ProfileError(409, 'MQVPN reorder setting has an invalid format')
    for key in ('max_wait_ms', 'cap_packets'):
        value = result['reorder'][key]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1048576:
            raise ProfileError(409, 'MQVPN reorder setting has an invalid format')
    return result


class Runtime:
    """Only these file/sysctl operations are allowed to alter service settings."""
    def __init__(self, control_api, ensure_nanbbr, read_nanbbr,
                 mq_config='/etc/mqvpn/server.json',
                 sysctl_file='/etc/sysctl.d/90-shadowsocks.conf',
                 nanbbr_file='/etc/openmptcprouter-vps-admin/nanbbr-var.json'):
        self.control_api = control_api
        self.ensure_nanbbr = ensure_nanbbr
        self.read_nanbbr = read_nanbbr
        self.mq_config, self.sysctl_file, self.nanbbr_file = mq_config, sysctl_file, nanbbr_file

    def ensure_recovery_ready(self):
        try:
            subprocess.run(['systemctl', 'is-active', '--quiet', 'omr-profile-recovery.timer'],
                           check=True, timeout=5)
            # The independent watchdog accepts only local control sockets.
            # Prove it can query the actual configured daemon before changing it.
            info = watchdog_control({'cmd': 'get_build_info'}, self.mq_config)
            if not info.get('ok'):
                raise RuntimeError('MQVPN local control did not respond')
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            raise ProfileError(503, 'Profile recovery watchdog is unavailable') from error

    def _build_info(self):
        info = self.control_api({'cmd': 'get_build_info'})
        if not isinstance(info, dict) or not info.get('ok'):
            raise ProfileError(503, 'MQVPN control API is unavailable')
        return info

    def current(self):
        config = _read_json(self.mq_config)
        mq = _mq_settings(config)
        info = self._build_info()
        if info.get('scheduler') != mq['scheduler']:
            raise ProfileError(503, 'MQVPN running scheduler does not match saved configuration')
        aggression = self.read_nanbbr()
        if aggression is None:
            for cc in ('nanbbr1_var', 'nanbbr2_var', 'nanbbr3_var'):
                try:
                    value = int(Path('/sys/module/tcp_' + cc + '/parameters/aggressiveness').read_text().strip())
                    if 1 <= value <= 100:
                        aggression = value
                        break
                except (OSError, ValueError):
                    continue
        scheduler = _sysctl(_scheduler_key())
        cc = _sysctl('net.ipv4.tcp_congestion_control')
        if not re.fullmatch(r'[a-z0-9_]{1,40}', scheduler) or not re.fullmatch(r'[a-z0-9_]{1,40}', cc):
            raise ProfileError(409, 'MPTCP profile settings have an invalid format')
        return {'mptcp': {'scheduler': scheduler,
                          'congestion_control': cc,
                          'nanbbr_aggressiveness': aggression}, 'mqvpn': mq}

    def availability(self):
        info = self._build_info()
        if info.get('version') != '0.16.2':
            raise ProfileError(409, 'This MQVPN version has not been validated for profile switching')
        try:
            schedulers = set(Path('/proc/sys/net/mptcp/available_schedulers').read_text().split())
        except OSError:
            schedulers = {'default', _sysctl(_scheduler_key())}
            # Only report installed BPF schedulers that are actually registered.
            try:
                registered = subprocess.run(['bpftool', '-j', 'struct_ops', 'show'],
                    check=True, capture_output=True, text=True, timeout=5).stdout
                parsed = json.loads(registered)
                def strings(obj):
                    if isinstance(obj, str):
                        yield obj
                    elif isinstance(obj, list):
                        for entry in obj: yield from strings(entry)
                    elif isinstance(obj, dict):
                        for entry in obj.values(): yield from strings(entry)
                names = set(strings(parsed))
                for file in glob.glob('/usr/share/bpf/scheduler/mptcp_*.o'):
                    name = Path(file).stem.removeprefix('mptcp_')
                    if name in names: schedulers.add(name)
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
        try:
            available = set(Path('/proc/sys/net/ipv4/tcp_available_congestion_control').read_text().split())
        except OSError:
            available = set()
        for name in TCP_CC:
            if name in available or name in ('reno', 'cubic', 'bbr'):
                continue
            try:
                rc = subprocess.run(['modprobe', '-n', '-q', 'tcp_' + name],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    timeout=1, check=False).returncode
                if rc == 0: available.add(name)
            except (OSError, subprocess.SubprocessError):
                pass
        mq_schedulers = list(MQ_SCHEDULERS)
        fec_schemes = []
        if bool(info.get('fec_enabled')):
            try:
                package = subprocess.run(['dpkg-query', '-W', '-f=${Version}', 'mqvpn'],
                    check=True, capture_output=True, text=True, timeout=5).stdout.strip()
                expected_binary = VERIFIED_FEC_BINARIES.get(package)
                if expected_binary and _sha256_file('/usr/bin/mqvpn') == expected_binary:
                    fec_schemes = list(FEC_SCHEMES)
            except (OSError, subprocess.SubprocessError):
                pass
        if not fec_schemes:
            mq_schedulers.remove('backup_fec')
        return {'tcp_schedulers': sorted(schedulers), 'tcp_cc': sorted(available.intersection(TCP_CC)),
                'mq_schedulers': mq_schedulers, 'mq_cc': list(MQ_CC),
                'fec_schemes': fec_schemes}

    def snapshot(self, requested):
        """Record exactly managed fields; never journal other config or keys."""
        current = self.current()
        mq_cfg = _read_json(self.mq_config)
        old_mq = {}
        for key in requested['mqvpn']:
            if key == 'reorder':
                block = mq_cfg.get('reorder') or {}
                old_mq[key] = {'parent_present': 'reorder' in mq_cfg, 'fields': {
                    field: {'present': field in block, 'value': block.get(field)}
                    for field in requested['mqvpn']['reorder']}}
            else:
                old_mq[key] = {'present': key in mq_cfg, 'value': mq_cfg.get(key)}
        selected = [_scheduler_key(), 'net.ipv4.tcp_congestion_control']
        try:
            lines = Path(self.sysctl_file).read_text(encoding='utf-8').splitlines(keepends=True)
            file_present = True
        except FileNotFoundError:
            lines = []; file_present = False
        saved_lines = []
        for line in lines:
            if _line_key(line) in selected:
                clean = line.split('#', 1)[0].strip()
                if not re.fullmatch(r'[a-zA-Z0-9_.]+\s*=\s*[a-zA-Z0-9_-]+', clean):
                    raise ProfileError(409, 'Cannot safely snapshot MPTCP persistent settings')
                saved_lines.append(clean + '\n')
        nan = None
        if requested['mptcp'].get('nanbbr_aggressiveness') is not None:
            try:
                data = _read_json(self.nanbbr_file)
                nan = {'file_present': True, 'present': 'aggressiveness' in data,
                       'value': data.get('aggressiveness')}
            except FileNotFoundError:
                nan = {'file_present': False, 'present': False, 'value': None}
            nan['parameters'] = {}
            for cc in ('nanbbr1_var', 'nanbbr2_var', 'nanbbr3_var'):
                try:
                    parameter = self.ensure_nanbbr(cc)
                    nan['parameters'][cc] = Path(parameter).read_text().strip()
                except (OSError, RuntimeError):
                    if cc == requested['mptcp']['congestion_control']:
                        raise ProfileError(409, 'Selected NanBBR aggression parameter is unavailable')
            if not nan['parameters']:
                raise ProfileError(409, 'NanBBR aggression parameter is unavailable')
        return {'current': current, 'mq_fields': old_mq,
                'sysctl': {'file_present': file_present, 'keys': selected, 'lines': saved_lines},
                'nanbbr': nan}

    def validate(self, requested):
        available = self.availability()
        tcp, mq = requested['mptcp'], requested['mqvpn']
        if tcp['scheduler'] not in available['tcp_schedulers']:
            raise ProfileError(409, 'TCP scheduler is unavailable')
        if tcp['congestion_control'] not in available['tcp_cc']:
            raise ProfileError(409, 'TCP congestion control is unavailable')
        if tcp['congestion_control'].endswith('_var') and tcp.get('nanbbr_aggressiveness') is None:
            raise ProfileError(422, 'NanBBR variable aggression is required')
        if mq['scheduler'] not in available['mq_schedulers'] or mq['cc'] not in available['mq_cc']:
            raise ProfileError(409, 'MQVPN scheduler or congestion control is unavailable')
        old_mq = self.current()['mqvpn']
        if mq.get('fec_enable', old_mq['fec_enable']) and mq.get('fec_scheme', old_mq['fec_scheme']) not in available['fec_schemes']:
            raise ProfileError(409, 'Requested MQVPN FEC capability is unavailable')

    def _set_sysctls(self, mptcp):
        previous = (_sysctl(_scheduler_key()), _sysctl('net.ipv4.tcp_congestion_control'))
        cc = mptcp['congestion_control']
        if cc not in ('reno', 'cubic', 'bbr'):
            available = _sysctl('net.ipv4.tcp_available_congestion_control').split()
            if cc not in available:
                load_tcp_cc(cc)
        pairs = ((_scheduler_key(), mptcp['scheduler']), ('net.ipv4.tcp_congestion_control', cc))
        for key, value in pairs:
            _sysctl(key, value)
            if _sysctl(key) != str(value):
                raise RuntimeError('MPTCP settings readback mismatch')
        if mptcp.get('nanbbr_aggressiveness') is not None:
            value = mptcp['nanbbr_aggressiveness']
            changed = 0
            for ccname in ('nanbbr1_var', 'nanbbr2_var', 'nanbbr3_var'):
                try:
                    param = self.ensure_nanbbr(ccname)
                except (OSError, RuntimeError):
                    if ccname == cc: raise
                    continue
                Path(param).write_text(str(value))
                if Path(param).read_text().strip() != str(value):
                    raise RuntimeError('NanBBR readback mismatch')
                changed += 1
            if not changed: raise RuntimeError('NanBBR parameter could not be written')
            try: data = _read_json(self.nanbbr_file)
            except FileNotFoundError: data = {'version': 1}
            data['aggressiveness'] = value
            _write_json(self.nanbbr_file, data)
        _rewrite_sysctl(self.sysctl_file, [key for key, _ in pairs],
                        [f'{key}={value}\n' for key, value in pairs])
        if previous != (mptcp['scheduler'], cc):
            _restart_mptcp_dependents()

    def _set_mq(self, fields, restore=False):
        cfg = _read_json(self.mq_config)
        before = copy.deepcopy(cfg)
        for key, value in fields.items():
            if key == 'reorder':
                block = cfg.get('reorder') or {}
                if not isinstance(block, dict): raise RuntimeError('Invalid MQVPN reorder state')
                if restore:
                    for subkey, saved in value['fields'].items():
                        if saved['present']: block[subkey] = saved['value']
                        else: block.pop(subkey, None)
                    if not value['parent_present'] and not block: cfg.pop('reorder', None)
                    else: cfg['reorder'] = block
                else:
                    block.update(value); cfg['reorder'] = block
            elif restore:
                if value['present']: cfg[key] = value['value']
                else: cfg.pop(key, None)
            else:
                cfg[key] = value
        if cfg != before:
            _write_json(self.mq_config, cfg)
        if cfg != before or restore:
            subprocess.run(['systemctl', 'restart', 'mqvpn'], check=True, capture_output=True, timeout=30)
            subprocess.run(['systemctl', 'is-active', '--quiet', 'mqvpn'], check=True, timeout=8)
            deadline = time.monotonic() + 8
            while True:
                try:
                    if self._build_info().get('scheduler') == _mq_settings(cfg)['scheduler']: break
                except ProfileError:
                    pass
                if time.monotonic() >= deadline: raise RuntimeError('MQVPN runtime readback failed')
                time.sleep(.25)

    def apply(self, requested):
        self._set_sysctls(requested['mptcp'])
        self._set_mq(requested['mqvpn'])
        actual = self.current()
        for group in ('mptcp', 'mqvpn'):
            for key, value in requested[group].items():
                if value is None: continue
                if key == 'reorder':
                    if any(actual[group][key][k] != v for k, v in value.items()):
                        raise RuntimeError('MQVPN reorder readback mismatch')
                elif actual[group][key] != value:
                    raise RuntimeError('Profile settings readback mismatch')

    def restore(self, saved):
        failures = []
        try: self._set_mq(saved['mq_fields'], restore=True)
        except Exception: failures.append('MQVPN')
        previous = saved['current']['mptcp']
        try: _restore_scheduler(previous['scheduler'])
        except Exception: failures.append('MPTCP scheduler')
        cc = previous['congestion_control']
        try:
            if cc not in _sysctl('net.ipv4.tcp_available_congestion_control').split():
                load_tcp_cc(cc)
        except Exception: failures.append('TCP congestion module')
        for key, value in (('net.ipv4.tcp_congestion_control', cc),):
            try:
                _sysctl(key, value)
                if _sysctl(key) != str(value): raise RuntimeError('readback mismatch')
            except Exception: failures.append(key)
        try:
            prior = saved['sysctl']
            _rewrite_sysctl(self.sysctl_file, prior['keys'], prior['lines'], prior['file_present'])
        except Exception: failures.append('MPTCP persistent settings')
        if saved['nanbbr'] is not None:
            old = saved['nanbbr']
            for ccname, value in old['parameters'].items():
                try:
                    param = self.ensure_nanbbr(ccname)
                    Path(param).write_text(value)
                    if Path(param).read_text().strip() != value: raise RuntimeError('readback mismatch')
                except Exception: failures.append('NanBBR ' + ccname)
            try:
                try: obj = _read_json(self.nanbbr_file)
                except FileNotFoundError: obj = {}
                if old['present']: obj['aggressiveness'] = old['value']
                else: obj.pop('aggressiveness', None)
                if not old['file_present'] and not obj:
                    try: os.unlink(self.nanbbr_file)
                    except FileNotFoundError: pass
                else: _write_json(self.nanbbr_file, obj)
            except Exception: failures.append('NanBBR persistent settings')
        try: _restart_mptcp_dependents()
        except Exception: failures.append('MPTCP dependent services')
        if failures:
            raise RuntimeError('Could not restore ' + ', '.join(failures))


def _line_key(line):
    stripped = line.strip()
    if not stripped or stripped.startswith('#') or '=' not in stripped: return None
    return stripped.split('=', 1)[0].strip()


def _rewrite_sysctl(filename, keys, replacement, file_present=True):
    try:
        path = Path(filename)
        lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
        info = path.stat()
        mode = stat.S_IMODE(info.st_mode)
        owner = (info.st_uid, info.st_gid)
    except FileNotFoundError:
        lines = []; mode = 0o644; owner = None
    remain = [line for line in lines if _line_key(line) not in keys]
    if remain and not remain[-1].endswith('\n'): remain[-1] += '\n'
    result = ''.join(remain + list(replacement))
    if not file_present and not result:
        try: os.unlink(filename)
        except FileNotFoundError: pass
    else:
        _atomic_bytes(filename, result.encode(), mode, owner)


class ProfileManager:
    def __init__(self, runtime, journal='/var/lib/omr-profiles/transaction.json',
                 lock='/run/lock/omr-profile.lock', window=240, clock=time.time,
                 enable_timer=True, monotonic=_boot_time, boot_id=_boot_id):
        self.runtime, self.journal, self.lock = runtime, Path(journal), Path(lock)
        self.window, self.clock, self.enable_timer = window, clock, enable_timer
        self.monotonic, self.boot_id = monotonic, boot_id
        self.timer = None
        self.thread_lock = threading.RLock()

    @contextlib.contextmanager
    def locked(self):
        self.lock.parent.mkdir(parents=True, exist_ok=True)
        with self.thread_lock:
            fd = os.open(self.lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
                os.close(fd)
                raise RuntimeError('Profile lock is not a regular file owned by the service')
            handle = os.fdopen(fd, 'a+', encoding='ascii')
            with handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try: yield
                finally: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _load(self):
        try: return _read_json(self.journal)
        except FileNotFoundError: return None

    def _write(self, data):
        # Do not inherit a permissive mode from any pre-existing journal.
        self.journal.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        _atomic_bytes(self.journal, (json.dumps(data, indent=2, sort_keys=True) + '\n').encode(), 0o600)

    def _schedule(self, delay):
        if not self.enable_timer: return
        if self.timer: self.timer.cancel()
        self.timer = threading.Timer(max(.1, delay), self._on_timer)
        self.timer.daemon = True
        self.timer.start()

    def _remaining(self, state):
        # The wall-clock deadline is informational only. On reboot (or a
        # legacy/incomplete journal) rollback immediately; a timer from a
        # previous boot cannot be compared safely with the new uptime.
        if state.get('boot_id') != self.boot_id() or not isinstance(state.get('deadline_monotonic'), (int, float)):
            return 0
        return max(0, state['deadline_monotonic'] - self.monotonic())

    def _on_timer(self):
        try:
            with self.locked(): self._expire_locked()
        except Exception:
            self._schedule(30)

    def _rollback_locked(self, state):
        try:
            self.runtime.restore(state['before'])
            state['state'] = 'rolled_back'; state.pop('error', None)
        except Exception as error:
            state['state'] = 'rollback_failed'; state['error'] = str(error)
        self._write(state)
        if state['state'] == 'rollback_failed': self._schedule(30)
        return state

    def _expire_locked(self):
        state = self._load()
        if not state: return
        if state['state'] == 'preparing' and self._remaining(state) <= 0:
            # Preflight can load modules but has not written any managed values.
            state['state'] = 'rolled_back'
            self._write(state)
        elif state['state'] in ('applying', 'pending') and self._remaining(state) <= 0:
            self._rollback_locked(state)
        elif state['state'] == 'rollback_failed':
            self._rollback_locked(state)
        elif state['state'] == 'pending':
            self._schedule(self._remaining(state))

    def startup(self):
        with self.locked():
            state = self._load()
            if state and state['state'] == 'preparing':
                state['state'] = 'rolled_back'
                self._write(state)
            elif state and state['state'] == 'applying':
                self._rollback_locked(state)
            else:
                self._expire_locked()

    def capabilities(self):
        with self.locked():
            self._expire_locked()
            return {'supported': True, 'version': 1, 'current': self.runtime.current(),
                    'availability': self.runtime.availability()}

    def status(self, transaction):
        if not TRANSACTION_RE.fullmatch(transaction): raise ProfileError(422, 'Invalid transaction')
        with self.locked():
            self._expire_locked()
            state = self._load()
            if not state or state.get('transaction') != transaction:
                return {'result': 'done', 'transaction': transaction, 'state': 'unknown', 'deadline': None, 'seconds_remaining': None}
            return {key: state.get(key) for key in ('transaction', 'state', 'deadline', 'error')} | {
                'result': 'done', 'seconds_remaining': int(self._remaining(state))}

    def apply(self, transaction, requested):
        if not TRANSACTION_RE.fullmatch(transaction): raise ProfileError(422, 'Invalid transaction')
        with self.locked():
            self._expire_locked()
            existing = self._load()
            if existing and existing['transaction'] == transaction:
                # A duplicate after an uncertain response is never reapplied.
                if existing.get('target') != requested:
                    raise ProfileError(409, 'Transaction ID is already associated with different settings')
                if existing['state'] not in ('pending', 'confirmed'):
                    raise ProfileError(409, 'Profile transaction is not applicable')
                return {'result': 'done', 'transaction': transaction, 'state': existing['state'],
                        'deadline': existing['deadline'], 'pending': existing['state'] == 'pending',
                        'seconds_remaining': int(self._remaining(existing))}
            if existing and existing['state'] in ('preparing', 'applying', 'pending', 'rollback_failed'):
                raise ProfileError(409, 'Another profile transaction is unresolved')
            # Journal before preflight: the client's POST can time out while
            # a slow module probe is still running. Its rollback/status request
            # will then find this ID instead of incorrectly seeing "unknown".
            state = {'transaction': transaction, 'state': 'preparing',
                     'deadline': int(self.clock()) + self.window,
                     'deadline_monotonic': self.monotonic() + self.window,
                     'boot_id': self.boot_id(),
                     'target': copy.deepcopy(requested)}
            self._write(state)
            self._schedule(self._remaining(state))
            try:
                if hasattr(self.runtime, 'ensure_recovery_ready'):
                    self.runtime.ensure_recovery_ready()
                self.runtime.validate(requested)
                state['before'] = self.runtime.snapshot(requested)
                state['state'] = 'applying'
                self._write(state)
                self.runtime.apply(requested)
                state['state'] = 'pending'
                self._write(state)
            except Exception as error:
                if 'before' not in state:
                    state['state'] = 'rolled_back'
                    self._write(state)
                    if isinstance(error, ProfileError): raise
                    raise ProfileError(503, 'Profile validation failed; settings were not changed') from error
                state = self._rollback_locked(state)
                raise ProfileError(503, 'Profile apply failed; ' +
                                   ('rollback incomplete' if state['state'] == 'rollback_failed' else 'previous settings restored')) from error
            self._schedule(self._remaining(state))
            return {'result': 'done', 'transaction': transaction, 'state': 'pending',
                    'deadline': state['deadline'], 'pending': True,
                    'seconds_remaining': int(self._remaining(state))}

    def finish(self, transaction, confirm):
        if not TRANSACTION_RE.fullmatch(transaction): raise ProfileError(422, 'Invalid transaction')
        with self.locked():
            self._expire_locked()
            state = self._load()
            if not state or state['transaction'] != transaction:
                raise ProfileError(404, 'Profile transaction not found')
            if confirm:
                if state['state'] == 'confirmed': pass
                elif state['state'] != 'pending': raise ProfileError(409, 'Profile transaction cannot be confirmed')
                else:
                    state['state'] = 'confirmed'; self._write(state)
                    if self.timer: self.timer.cancel()
            elif state['state'] == 'rolled_back': pass
            elif state['state'] == 'confirmed': raise ProfileError(409, 'Confirmed profile cannot be rolled back')
            else:
                state = self._rollback_locked(state)
                if state['state'] == 'rollback_failed':
                    raise ProfileError(503, 'Profile rollback is incomplete')
            return {'result': 'done', 'transaction': transaction,
                    'state': state['state'], 'deadline': state['deadline'],
                    'seconds_remaining': int(self._remaining(state))}

    @contextlib.contextmanager
    def guard_existing_mutation(self):
        with self.locked():
            self._expire_locked()
            state = self._load()
            if state and state['state'] in ('preparing', 'applying', 'pending', 'rollback_failed'):
                raise ProfileError(409, 'A profile change is pending')
            yield
