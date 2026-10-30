#!/usr/bin/env python3
"""Private state and command backend for the OMR road-warrior manager.

Only client-wg0 is managed. WireGuard server keys and client profiles are never
written to logs; peer identity and policy are based on public keys plus /32s.
"""
import argparse
import base64
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import time

POOL = ipaddress.IPv4Network('10.255.246.0/24')
INTERFACE = 'client-wg0'
NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$')
STATES = {'active', 'disabled', 'adding', 'disabling', 'removing', 'quarantine'}


class ManagerError(Exception):
    pass


def valid_key(value):
    if not isinstance(value, str) or len(value) != 44:
        return False
    try:
        return len(base64.b64decode(value, validate=True)) == 32
    except (ValueError, TypeError):
        return False


def valid_peer_ip(value):
    if not isinstance(value, str):
        return False
    try:
        address = ipaddress.IPv4Address(value)
        return address in POOL and address not in (POOL.network_address, POOL.broadcast_address, POOL[1])
    except (ipaddress.AddressValueError, TypeError):
        return False


def nft_set_contains(elements, address):
    """Handle nft JSON singleton, prefix and interval representations."""
    try:
        wanted = ipaddress.IPv4Address(address)
        for element in elements or []:
            if isinstance(element, str):
                if wanted in ipaddress.IPv4Network(element, strict=False):
                    return True
            elif isinstance(element, dict):
                if 'elem' in element:
                    value = element['elem']
                    if isinstance(value, dict) and 'val' in value:
                        value = value['val']
                    if nft_set_contains([value], address):
                        return True
                if 'prefix' in element:
                    prefix = element['prefix']
                    if wanted in ipaddress.IPv4Network(str(prefix['addr']) + '/' + str(prefix['len']), strict=False):
                        return True
                if 'range' in element:
                    first, last = element['range']
                    if ipaddress.IPv4Address(first) <= wanted <= ipaddress.IPv4Address(last):
                        return True
        return False
    except (ValueError, KeyError, TypeError):
        # Never report an unparseable firewall element as an open grant.
        return False


def parse_config(text):
    """Read peer public fields without returning interface/private key fields."""
    section = ''; peers = []; current = None; addresses = []
    for line in text.splitlines():
        s = line.split('#', 1)[0].strip()
        if not s:
            continue
        if s.startswith('[') and s.endswith(']'):
            section = s[1:-1].strip().lower()
            current = {} if section == 'peer' else None
            if current is not None:
                peers.append(current)
            continue
        if '=' not in s:
            raise ManagerError('Invalid WireGuard configuration')
        key, value = (x.strip() for x in s.split('=', 1))
        key = key.lower()
        if section == 'interface' and key == 'address':
            addresses += [v.strip() for v in value.split(',')]
        if section == 'peer' and key in ('publickey', 'allowedips'):
            if key in current:
                raise ManagerError('Ambiguous WireGuard peer fields')
            current[key] = value
    try:
        interfaces = [ipaddress.ip_interface(x) for x in addresses]
    except ValueError as exc:
        raise ManagerError('Invalid WireGuard interface address') from exc
    if not any(isinstance(x, ipaddress.IPv4Interface) and x.ip == POOL[1] and x.network == POOL for x in interfaces):
        raise ManagerError('client-wg0 does not use the expected IPv4 pool')
    result = {}; used = set()
    for peer in peers:
        key = peer.get('publickey', '')
        ips = [x.strip() for x in peer.get('allowedips', '').split(',') if x.strip()]
        if not valid_key(key) or key in result or len(ips) != 1:
            raise ManagerError('A peer has ambiguous public key or AllowedIPs; migrate it manually first')
        try:
            net = ipaddress.ip_network(ips[0], strict=True)
        except ValueError as exc:
            raise ManagerError('A peer has an invalid AllowedIPs value') from exc
        if not isinstance(net, ipaddress.IPv4Network) or net.prefixlen != 32 or not valid_peer_ip(str(net.network_address)):
            raise ManagerError('Every existing peer must have one unique /32 in the client-wg0 pool')
        ip = str(net.network_address)
        if ip in used:
            raise ManagerError('Overlapping WireGuard peer addresses require manual migration')
        used.add(ip); result[key] = ip
    return result


def read_registry(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('peers'), list):
        raise ManagerError('Invalid peer registry')
    keys = set(); addresses = set(); names = set()
    for p in data['peers']:
        if (not isinstance(p, dict) or not isinstance(p.get('name'), str) or
                not NAME.fullmatch(p['name']) or not valid_key(p.get('public_key'))):
            raise ManagerError('Invalid peer registry entry')
        if not valid_peer_ip(p.get('ip')) or not isinstance(p.get('state'), str) or p['state'] not in STATES:
            raise ManagerError('Invalid peer registry address or state')
        if type(p.get('legacy')) is not bool or type(p.get('lan')) is not bool:
            raise ManagerError('Invalid peer registry permissions')
        if not isinstance(p.get('mode'), str) or p['mode'] not in ('split', 'full'):
            raise ManagerError('Invalid peer registry route mode')
        if p['public_key'] in keys or p['ip'] in addresses or p['name'].lower() in names:
            raise ManagerError('Duplicate peer registry identity')
        keys.add(p['public_key']); addresses.add(p['ip']); names.add(p['name'].lower())
    return data


def policy_from_state(data, configured, live):
    """Return exact-IP LAN grants and restricted INPUT peers; reject drift.

    Configured/runtime peers which are unknown to the registry fail closed.
    An inactive legacy key never grants a newly allocated peer its old IP.
    """
    if not isinstance(configured, dict) or not isinstance(live, dict):
        raise ManagerError('Peer information unavailable')
    by_key = {p['public_key']: p for p in data['peers']}
    grants = set(); restricted = set()
    for key, ip in configured.items():
        if not valid_key(key) or not valid_peer_ip(ip):
            raise ManagerError('Invalid configured peer identity')
        peer = by_key.get(key)
        matching = peer and peer['ip'] == ip and peer['state'] == 'active' and live.get(key) == ip
        if matching and peer['lan']:
            grants.add(ip)
        if not matching or not peer['legacy']:
            restricted.add(ip)
    for key, ip in live.items():
        if not valid_key(key) or not valid_peer_ip(ip):
            raise ManagerError('Invalid live peer identity')
        peer = by_key.get(key)
        if not peer or peer['ip'] != ip or peer['state'] != 'active' or configured.get(key) != ip or not peer['legacy']:
            restricted.add(ip)
        # Never grant an address whose current owner differs from the registry.
        if configured.get(key) != ip or not peer or peer['ip'] != ip:
            grants.discard(ip)
    for peer in data['peers']:
        if not peer['legacy'] or peer['state'] != 'active':
            restricted.add(peer['ip'])
    return sorted(grants, key=ipaddress.IPv4Address), sorted(restricted, key=ipaddress.IPv4Address)


def parse_live_allowed(text):
    out = {}; used = set()
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 2 or not valid_key(parts[0]):
            raise ManagerError('Cannot parse WireGuard peer state')
        try:
            net = ipaddress.ip_network(parts[1], strict=True)
        except ValueError as exc:
            raise ManagerError('A live peer has an unsupported AllowedIPs value') from exc
        if not isinstance(net, ipaddress.IPv4Network) or net.prefixlen != 32 or not valid_peer_ip(str(net.network_address)):
            raise ManagerError('A live peer does not have one /32 in the expected pool')
        ip = str(net.network_address)
        if ip in used or parts[0] in out:
            raise ManagerError('Live WireGuard addresses overlap')
        out[parts[0]] = ip; used.add(ip)
    return out


def peer_policy(registry_path, config_path, command=None):
    """Fail closed for absent, corrupted or inconsistent initialized state."""
    try:
        data = read_registry(registry_path)
        configured = parse_config(config_path.read_text(encoding='utf-8'))
        runner = command or subprocess.check_output
        live = parse_live_allowed(runner(['wg', 'show', INTERFACE, 'allowed-ips'], text=True,
                                          stderr=subprocess.DEVNULL))
        return policy_from_state(data, configured, live)
    except (OSError, ValueError, TypeError, json.JSONDecodeError, subprocess.SubprocessError, ManagerError):
        return [], [str(POOL)]


def atomic_write(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
        dfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def add_peer_block(text, key, ip):
    return text.rstrip() + '\n\n[Peer]\nPublicKey = ' + key + '\nAllowedIPs = ' + ip + '/32\n'


def remove_peer_block(text, key):
    lines = text.splitlines(keepends=True); starts = []
    for i, line in enumerate(lines):
        if re.fullmatch(r'\s*\[peer\]\s*(?:#.*)?(?:\r?\n)?', line, flags=re.I):
            starts.append(i)
    for n, start in enumerate(starts):
        end = starts[n+1] if n+1 < len(starts) else len(lines)
        for line in lines[start:end]:
            field = line.split('#', 1)[0].strip().split('=', 1)
            if len(field) == 2 and field[0].strip().lower() == 'publickey' and field[1].strip() == key:
                return ''.join(lines[:start] + lines[end:])
    raise ManagerError('Peer is missing from the WireGuard configuration')


class Manager:
    def __init__(self, root=Path('/'), runner=subprocess.run, policy_apply=None):
        self.root = Path(root)
        self.config = self.root / 'etc/wireguard/client-wg0.conf'
        self.legacy_profile = self.root / 'root/wireguard-client.conf'
        self.policy_dir = self.root / 'etc/openmptcprouter-vps-admin'
        self.state_dir = self.policy_dir / 'wg-remote-manager'
        self.registry = self.state_dir / 'peers.json'
        self.marker = self.state_dir / 'initialized'
        self.gate_state = self.policy_dir / 'wg-remote-lan-access.enabled'
        self.lock_path = self.policy_dir / 'wg-remote-lan-access.lock'
        self.clients = self.root / 'etc/wireguard/omr-remote-clients'
        self.runner = runner
        self.policy_apply = policy_apply

    def lock(self):
        self.policy_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd

    def command(self, args, *, input=None, check=True):
        result = self.runner(args, input=input, text=True, capture_output=True, check=False)
        if check and result.returncode:
            # Do not expose command stderr or anything that may contain key data.
            raise ManagerError('A WireGuard operation failed; check service state')
        return result

    def live(self, allow_down=False):
        result = self.command(['wg', 'show', INTERFACE, 'allowed-ips'], check=False)
        if result.returncode:
            if allow_down:
                return None
            raise ManagerError('client-wg0 is not running')
        return parse_live_allowed(result.stdout)

    def config_text(self):
        try:
            return self.config.read_text(encoding='utf-8')
        except OSError as exc:
            raise ManagerError('client-wg0 configuration is unavailable') from exc

    def persist(self, data):
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.state_dir, 0o700)
        atomic_write(self.registry, json.dumps(data, sort_keys=True, indent=2) + '\n')
        if not self.marker.exists():
            atomic_write(self.marker, '1\n')

    def reconcile(self):
        if self.policy_apply is not None:
            self.policy_apply(); return
        # The caller already owns the helper's lock; call its reconciliation
        # directly rather than spawning a second process that deadlocks on it.
        import importlib.machinery
        import importlib.util
        helper = self.root / 'usr/local/sbin/wg-remote-lan-route'
        loader = importlib.machinery.SourceFileLoader('omr_wg_route_for_manager', str(helper))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec); loader.exec_module(module)
        module.CONFIG = self.policy_dir / 'omr-admin-config.json'
        module.STATE = self.gate_state
        module.NFT_RULESET = self.root / 'etc/nftables/omr.nft'
        module.MQVPN_CONFIG = self.root / 'etc/mqvpn/server.json'
        module.PEER_REGISTRY = self.registry
        module.WG_CONFIG = self.config
        try:
            if 'set wg_remote_peer_lan_v4' not in module.NFT_RULESET.read_text(encoding='utf-8'):
                raise ManagerError('Per-client firewall rules are unavailable')
        except (OSError, UnicodeError) as exc:
            raise ManagerError('Per-client firewall rules are unavailable') from exc
        options = argparse.Namespace(config=module.CONFIG, dry_run=False, tunnel_dev=None, lan_access=None)
        module.reconcile(options, module.lan_access_enabled())

    def initialize(self, defer_firewall=False):
        fd = self.lock()
        try:
            if self.registry.exists():
                data = read_registry(self.registry)
                if not self.marker.exists():
                    atomic_write(self.marker, '1\n')
                return data
            if self.marker.exists():
                raise ManagerError('The peer registry is missing; restore it before continuing')
            configured = parse_config(self.config_text())
            live = self.live(allow_down=True)
            if live is not None and live != configured:
                raise ManagerError('Live/configured WireGuard peers differ; reconcile them before migration')
            # Existing keys retain their historic global-checkbox LAN behavior.
            peers = [{'name':'legacy_' + ip.rsplit('.', 1)[1], 'public_key':key, 'ip':ip,
                      'legacy':True, 'lan':True, 'state':'active', 'mode':'split'}
                     for key, ip in sorted(configured.items(), key=lambda x: ipaddress.IPv4Address(x[1]))]
            data = {'version':1, 'peers':peers}; self.persist(data)
            if not defer_firewall and live is not None:
                self.reconcile()
            return data
        finally:
            os.close(fd)

    def load(self):
        if not self.marker.exists() or not self.registry.exists():
            raise ManagerError('Peer manager is not initialized; run init first')
        try:
            return read_registry(self.registry)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ManagerError('Peer registry is unavailable; access remains restricted') from exc

    def ensure_consistent(self, data):
        configured = parse_config(self.config_text()); live = self.live()
        expected = {p['public_key']:p['ip'] for p in data['peers'] if p['state'] == 'active'}
        if configured != live or configured != expected:
            raise ManagerError('Live peers, configuration and registry differ; run recover or reconcile manually')

    def find(self, data, name):
        for peer in data['peers']:
            if peer['name'].lower() == name.lower():
                return peer
        raise ManagerError('Client not found')

    def allocate(self, data, requested=None):
        used = {p['ip'] for p in data['peers']}
        used.update(parse_config(self.config_text()).values())
        live = self.live(); used.update(live.values())
        if requested:
            if not valid_peer_ip(requested) or requested in used:
                raise ManagerError('Requested address is invalid or already reserved')
            return requested
        for address in list(POOL.hosts())[1:]:
            if str(address) not in used:
                return str(address)
        raise ManagerError('No free client addresses remain')

    def policy_ready(self):
        for name in ('wg_remote_peer_lan_v4', 'wg_remote_peer_restrict_v4'):
            result = self.command(['nft', 'list', 'set', 'inet', 'omr', name], check=False)
            if result.returncode:
                raise ManagerError('Per-client firewall policy is not loaded; finish the VPS upgrade first')

    def endpoint(self, supplied=None):
        endpoint = supplied
        if not endpoint and self.legacy_profile.is_file():
            for line in self.legacy_profile.read_text(encoding='utf-8').splitlines():
                if re.match(r'^\s*Endpoint\s*=', line, re.I):
                    endpoint = line.split('=', 1)[1].strip(); break
        if not endpoint or len(endpoint) > 260 or not re.fullmatch(r'(?:\[[0-9A-Fa-f:.]+\]|[A-Za-z0-9.-]+):[0-9]{1,5}', endpoint):
            raise ManagerError('A valid public endpoint host:port is required')
        if int(endpoint.rsplit(':', 1)[1]) not in range(1, 65536):
            raise ManagerError('Invalid WireGuard endpoint port')
        return endpoint

    def profile_path(self, peer):
        if peer['legacy']:
            return self.legacy_profile if peer['ip'] == str(POOL[2]) else None
        return self.clients / (peer['name'] + '.conf')

    def create_profile(self, peer, secret, server_key, endpoint):
        if not valid_key(secret) or not valid_key(server_key):
            raise ManagerError('Unable to generate valid WireGuard keys')
        text = ('[Interface]\nPrivateKey = ' + secret + '\nAddress = ' + peer['ip'] + '/32\n'
                'DNS = 1.1.1.1\n\n[Peer]\nPublicKey = ' + server_key + '\nEndpoint = ' + endpoint +
                '\nAllowedIPs = ' + ('0.0.0.0/0' if peer['mode'] == 'full' else '10.255.0.0/16') +
                '\nPersistentKeepalive = 25\n')
        self.clients.mkdir(parents=True, exist_ok=True, mode=0o700); os.chmod(self.clients, 0o700)
        atomic_write(self.profile_path(peer), text)

    def add(self, name, ip=None, mode='split', endpoint=None):
        if not NAME.fullmatch(name or '') or mode not in ('split', 'full'):
            raise ManagerError('Name must contain 1-32 letters, digits, underscores or hyphens')
        fd = self.lock()
        try:
            data = self.load(); self.ensure_consistent(data)
            self.policy_ready()
            if any(p['name'].lower() == name.lower() for p in data['peers']):
                raise ManagerError('A client with this name already exists')
            ip = self.allocate(data, ip); endpoint = self.endpoint(endpoint)
            private = self.command(['wg', 'genkey']).stdout.strip()
            public = self.command(['wg', 'pubkey'], input=private+'\n').stdout.strip()
            server_key = self.command(['wg', 'show', INTERFACE, 'public-key']).stdout.strip()
            if not valid_key(public) or public in {p['public_key'] for p in data['peers']}:
                raise ManagerError('Could not generate a unique public key')
            peer = {'name':name,'public_key':public,'ip':ip,'legacy':False,'lan':False,
                    'state':'adding','mode':mode}
            if self.profile_path(peer).exists():
                raise ManagerError('A profile file already exists for this name; resolve it before adding')
            self.create_profile(peer, private, server_key, endpoint)
            data['peers'].append(peer); self.persist(data)
            # Publish deny/restrict before the key or its address can carry traffic.
            self.reconcile()
            text = self.config_text(); parse_config(text)
            atomic_write(self.config, add_peer_block(text, public, ip))
            self.command(['wg', 'set', INTERFACE, 'peer', public, 'allowed-ips', ip+'/32'])
            # SaveConfig or an external editor can race a running interface.
            # Do not commit an active record if either view lost this peer;
            # the pending reservation can then be recovered fail-closed.
            if parse_config(self.config_text()).get(public) != ip or self.live().get(public) != ip:
                raise ManagerError('Peer changed during activation; run recover')
            peer['state'] = 'active'; self.persist(data); self.reconcile()
            self.ensure_consistent(data)
            return peer, self.profile_path(peer)
        finally:
            os.close(fd)

    def set_lan(self, name, allowed):
        fd = self.lock()
        try:
            data = self.load(); self.ensure_consistent(data); self.policy_ready(); peer = self.find(data, name)
            peer['lan'] = bool(allowed); self.persist(data)
            try:
                self.reconcile()
            except Exception as exc:
                if not allowed and peer['state'] == 'active':
                    # If the firewall cannot revoke, remove the key from the live
                    # interface. Keep the IP reserved and require recovery.
                    result = self.command(['wg', 'set', INTERFACE, 'peer', peer['public_key'], 'remove'], check=False)
                    peer['state'] = 'quarantine'; self.persist(data)
                    if result.returncode:
                        raise ManagerError('LAN revocation failed; the peer could not be disabled') from exc
                raise ManagerError('Policy refresh failed; check the tunnel and firewall') from exc
            return peer
        finally:
            os.close(fd)

    def disable(self, name, remove=False):
        fd = self.lock()
        try:
            data = self.load(); self.ensure_consistent(data); peer = self.find(data, name)
            if peer['state'] == 'disabled':
                if remove:
                    self.reconcile(); data['peers'].remove(peer); self.persist(data)
                    path = self.profile_path(peer)
                    if not peer['legacy'] and path:
                        path.unlink(missing_ok=True)
                return
            peer['state'] = 'removing' if remove else 'disabling'; self.persist(data)
            # Revoke LAN and restrict VPS input before the address can be reused.
            try:
                self.reconcile()
            except Exception as exc:
                # A failed firewall update must not leave a peer usable after a
                # requested disable/revoke. Keep its IP reserved for recovery.
                result = self.command(['wg', 'set', INTERFACE, 'peer', peer['public_key'], 'remove'], check=False)
                peer['state'] = 'quarantine'; self.persist(data)
                if result.returncode:
                    raise ManagerError('Peer revocation failed; the key could not be disabled') from exc
                raise ManagerError('Firewall refresh failed; the affected peer was disabled') from exc
            self.command(['wg', 'set', INTERFACE, 'peer', peer['public_key'], 'remove'])
            atomic_write(self.config, remove_peer_block(self.config_text(), peer['public_key']))
            if remove:
                data['peers'].remove(peer); self.persist(data)
                path = self.profile_path(peer)
                if not peer['legacy'] and path:
                    path.unlink(missing_ok=True)
            else:
                peer['state'] = 'disabled'; self.persist(data)
            self.reconcile(); self.ensure_consistent(data)
        finally:
            os.close(fd)

    def enable(self, name):
        fd = self.lock()
        try:
            data = self.load(); self.ensure_consistent(data); self.policy_ready(); peer = self.find(data, name)
            if peer['state'] != 'disabled':
                raise ManagerError('Client is not disabled')
            peer['state'] = 'adding'; self.persist(data); self.reconcile()
            atomic_write(self.config, add_peer_block(self.config_text(), peer['public_key'], peer['ip']))
            self.command(['wg', 'set', INTERFACE, 'peer', peer['public_key'], 'allowed-ips', peer['ip']+'/32'])
            if (parse_config(self.config_text()).get(peer['public_key']) != peer['ip'] or
                    self.live().get(peer['public_key']) != peer['ip']):
                raise ManagerError('Peer changed during activation; run recover')
            peer['state'] = 'active'; self.persist(data); self.reconcile(); self.ensure_consistent(data)
        finally:
            os.close(fd)

    def recover(self):
        """Abort incomplete mutations while keeping every unfinished IP reserved."""
        fd = self.lock()
        try:
            data = self.load(); text = self.config_text(); configured = parse_config(text)
            live = self.live(); changed = False
            for peer in data['peers']:
                if peer['state'] not in ('adding', 'disabling', 'removing', 'quarantine'):
                    continue
                # Key removal prevents access while restoring a consistent,
                # disabled peer; no unrelated peer is ever rewritten or removed.
                if peer['public_key'] in live:
                    self.command(['wg', 'set', INTERFACE, 'peer', peer['public_key'], 'remove'])
                if peer['public_key'] in configured:
                    text = remove_peer_block(text, peer['public_key']); configured.pop(peer['public_key'])
                peer['state'] = 'disabled'; changed = True
            if changed:
                atomic_write(self.config, text); self.persist(data)
            self.reconcile(); self.ensure_consistent(data)
        finally:
            os.close(fd)

    def verify_legacy_profile(self, text, peer):
        """Check identity before exporting an old profile without changing it."""
        section = ''; secrets_found = []; addresses = []
        try:
            for line in text.splitlines():
                stripped = line.split('#', 1)[0].strip()
                if stripped.startswith('[') and stripped.endswith(']'):
                    section = stripped[1:-1].strip().lower(); continue
                if section != 'interface' or '=' not in stripped:
                    continue
                field, value = (part.strip() for part in stripped.split('=', 1))
                if field.lower() == 'privatekey':
                    secrets_found.append(value)
                elif field.lower() == 'address':
                    addresses.extend(ipaddress.ip_interface(x.strip()) for x in value.split(','))
            ipv4 = [x.ip for x in addresses if isinstance(x, ipaddress.IPv4Interface)]
            if (len(secrets_found) != 1 or not valid_key(secrets_found[0]) or
                    len(ipv4) != 1 or str(ipv4[0]) != peer['ip']):
                raise ValueError('legacy identity mismatch')
            derived = self.command(['wg', 'pubkey'], input=secrets_found[0]+'\n').stdout.strip()
            if not valid_key(derived) or derived != peer['public_key']:
                raise ValueError('legacy identity mismatch')
        except (ValueError, TypeError, ManagerError) as exc:
            raise ManagerError('Legacy profile unavailable or does not match the registered peer') from exc

    def profile(self, name):
        fd = self.lock()
        try:
            data = self.load(); peer = self.find(data, name); path = self.profile_path(peer)
            if not path or not path.is_file():
                raise ManagerError('Private profile unavailable for this imported client')
            text = path.read_text(encoding='utf-8')
            if peer['legacy']:
                self.verify_legacy_profile(text, peer)
            if not peer['legacy'] and peer['mode'] == 'split' and peer['lan']:
                config = self.policy_dir / 'omr-admin-config.json'
                try:
                    doc = json.loads(config.read_text(encoding='utf-8'))
                    raw = doc['users'][0]['openmptcprouter'].get('lanips', [])
                    if not isinstance(raw, list) or not raw:
                        raise ValueError('router LAN is not synchronized')
                    nets = sorted({str(ipaddress.IPv4Network(x, strict=False)) for x in raw})
                    if any(not ipaddress.IPv4Network(x).is_private or
                           ipaddress.IPv4Network(x).prefixlen < 16 or
                           ipaddress.IPv4Network(x).overlaps(POOL) for x in nets):
                        raise ValueError('invalid LAN')
                except (OSError, ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
                    raise ManagerError('Router LAN settings are unavailable; cannot export a split LAN profile') from exc
                routes = ','.join(['10.255.0.0/16'] + nets)
                text, count = re.subn(r'(?mi)^AllowedIPs\s*=.*$', 'AllowedIPs = '+routes, text)
                if count != 1:
                    raise ManagerError('Client profile has ambiguous routes')
            return text
        finally:
            os.close(fd)

    def status(self):
        fd = self.lock()
        try:
            data = self.load(); configured = parse_config(self.config_text()); live = self.live(allow_down=True)
            def simple(field):
                result = self.command(['wg', 'show', INTERFACE, field], check=False)
                return {line.split()[0]:line.split()[1:] for line in result.stdout.splitlines() if len(line.split()) >= 2} if result.returncode == 0 else {}
            handshakes = simple('latest-handshakes'); transfer = simple('transfer')
            grants, _ = peer_policy(self.registry,self.config,lambda *a,**k: self.command(a[0]).stdout) if live is not None else ([],[])
            master = self.gate_state.is_file() and self.gate_state.read_text().strip() == 'allow'
            def nft_elements(name):
                result = self.command(['nft','-j','list','set','inet','omr',name],check=False)
                if result.returncode:
                    return None
                try:
                    tree=json.loads(result.stdout)
                    return next((x['set'].get('elem',[]) for x in tree.get('nftables',[]) if x.get('set',{}).get('name')==name),None)
                except (ValueError,TypeError,AttributeError):
                    return None
            peer_set=nft_elements('wg_remote_peer_lan_v4')
            lan_set=nft_elements('wg_remote_lan_v4')
            rows = []
            for p in data['peers']:
                h = handshakes.get(p['public_key'], ['0'])[0]
                t = transfer.get(p['public_key'], ['0','0'])
                try: age = max(0,int(time.time())-int(h)) if int(h) > 0 else None
                except ValueError: age = None
                firewall_known = peer_set is not None and lan_set is not None
                actual_open = bool(nft_set_contains(peer_set, p['ip']) and lan_set) if firewall_known else None
                rows.append({'name':p['name'],'ip':p['ip'],'state':p['state'],'legacy':p['legacy'],
                             'lan_requested':p['lan'],'master_lan':master,
                             'lan_peer_eligible':p['ip'] in grants,
                             # Report actual nft state even if persisted policy
                             # disagrees, so stale grants are never called closed.
                             'lan_firewall_open':actual_open,
                             'firewall_out_of_sync':bool(actual_open and not (master and p['ip'] in grants)) if firewall_known else None,
                             'last_handshake_age_seconds':age,
                             'handshake_recent':age is not None and age <= 240,
                             'rx_bytes':int(t[0]) if t and t[0].isdigit() else 0,
                             'tx_bytes':int(t[1]) if len(t)>1 and t[1].isdigit() else 0})
            expected = {p['public_key']:p['ip'] for p in data['peers'] if p['state'] == 'active'}
            return {'interface':INTERFACE,'master_lan':master,'peers':rows,
                    'consistent':live is not None and configured == live == expected}
        finally:
            os.close(fd)


def main():
    parser = argparse.ArgumentParser(description='Manage OMR remote WireGuard clients')
    commands = parser.add_subparsers(dest='command', required=True)
    ini=commands.add_parser('init'); ini.add_argument('--defer-firewall',action='store_true')
    add=commands.add_parser('add'); add.add_argument('name'); add.add_argument('--ip'); add.add_argument('--full',action='store_true'); add.add_argument('--endpoint')
    for command in ('disable','enable','remove','show','qr'):
        p=commands.add_parser(command); p.add_argument('name')
    lan=commands.add_parser('lan'); lan.add_argument('name'); lan.add_argument('permission',choices=('allow','deny'))
    status=commands.add_parser('status'); status.add_argument('--json',action='store_true')
    commands.add_parser('recover')
    args=parser.parse_args()
    if os.geteuid()!=0:
        print('Run as root.',file=sys.stderr); return 1
    manager=Manager()
    try:
        if args.command=='init':
            data=manager.initialize(args.defer_firewall); print(f"Initialized {len(data['peers'])} existing clients.")
        elif args.command=='add':
            peer,path=manager.add(args.name,args.ip,'full' if args.full else 'split',args.endpoint)
            print(f"Added {peer['name']} ({peer['ip']}); LAN disabled. Profile: {path}")
        elif args.command=='disable':manager.disable(args.name);print('Client disabled.')
        elif args.command=='enable':manager.enable(args.name);print('Client enabled.')
        elif args.command=='remove':manager.disable(args.name,remove=True);print('Client revoked. Legacy files, if any, were preserved.')
        elif args.command=='lan':
            p=manager.set_lan(args.name,args.permission=='allow')
            print('LAN permission saved. The global OMR LAN gate must also be enabled and the tunnel must be ready.' if p['lan'] else 'LAN permission revoked.')
        elif args.command=='status':
            info=manager.status()
            if args.json:
                print(json.dumps(info,indent=2))
            else:
                print('OMR LAN master gate:', 'enabled' if info['master_lan'] else 'disabled')
                print('Configured and live peers:', 'consistent' if info['consistent'] else 'DIFFERENT OR OFFLINE')
                print(f"{'Name':<20} {'Address':<16} {'State':<12} {'LAN':<12} {'Last handshake':<22} {'RX / TX bytes'}")
                for p in info['peers']:
                    age=p['last_handshake_age_seconds']
                    seen='never' if age is None else f'{age}s ago' + (' (recent)' if p['handshake_recent'] else '')
                    if p['lan_firewall_open'] is None:
                        lan='unknown'
                    else:
                        lan=('open (!)' if p['firewall_out_of_sync'] else 'open') if p['lan_firewall_open'] else ('requested' if p['lan_requested'] else 'denied')
                    print(f"{p['name']:<20} {p['ip']:<16} {p['state']:<12} {lan:<12} {seen:<22} {p['rx_bytes']} / {p['tx_bytes']}")
        elif args.command=='recover':manager.recover();print('Pending peer changes recovered; affected clients are disabled.')
        elif args.command=='show':sys.stdout.write(manager.profile(args.name))
        elif args.command=='qr':
            profile=manager.profile(args.name)
            try:subprocess.run(['qrencode','-t','ansiutf8','-l','L'],input=profile,text=True,check=True)
            except FileNotFoundError as exc:raise ManagerError('Install qrencode to display a QR code') from exc
    except (ManagerError,OSError,ValueError,subprocess.SubprocessError) as exc:
        # Report only deliberately sanitized errors; avoid command output and keys.
        print(str(exc) if isinstance(exc,ManagerError) else 'Operation failed; check WireGuard service and firewall.',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
