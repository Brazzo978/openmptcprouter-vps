#!/usr/bin/env python3
"""Isolated real WireGuard/nftables regression lab. Run as root on Linux.

Uses ephemeral keys and random network namespace names. Output contains only
sanitized assertion names; the temporary profiles and keys are always removed.
"""
import importlib.machinery
import importlib.util
import ipaddress
import json
import hashlib
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import omr_wg_manager as manager


def run(args, *, input=None, capture=False, check=True):
    result = subprocess.run(args, input=input, text=True, capture_output=True)
    if check and result.returncode:
        raise RuntimeError('isolated lab command failed: ' + Path(args[0]).name)
    return result.stdout.strip() if capture else result.returncode


def ns(name, *args, **kwargs):
    return run(['ip', 'netns', 'exec', name, *args], **kwargs)


def keypair():
    private = run(['wg', 'genkey'], capture=True)
    public = run(['wg', 'pubkey'], input=private + '\n', capture=True)
    return private, public


def private_file(path, secret):
    path.write_text(secret + '\n')
    path.chmod(0o600)


SERVER = r'''import socket,sys,threading
host,port,proto,mode=sys.argv[1],int(sys.argv[2]),sys.argv[3],sys.argv[4]
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM if proto=='udp' else socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind((host,port))
if proto=='udp':
 while True:
  data,peer=s.recvfrom(2048);s.sendto(data,peer)
else:
 s.listen(64)
 def handle(c,peer):
  with c:
   while True:
    try:
     data=c.recv(2048)
     if not data: return
     c.sendall(peer[0].encode() if mode=='reflect' else data)
    except OSError: return
 while True:
  c,peer=s.accept();threading.Thread(target=handle,args=(c,peer),daemon=True).start()
'''

PROBE = r'''import socket,sys
h,p,proto,expected=sys.argv[1],int(sys.argv[2]),sys.argv[3],sys.argv[4]
try:
 s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM if proto=='udp' else socket.SOCK_STREAM)
 s.settimeout(1.5);s.connect((h,p));s.sendall(b'probe');data=s.recv(128)
 sys.exit(0 if data.decode()==expected else 1)
except OSError: sys.exit(1)
'''

STREAM = r'''import socket,sys,time
s=socket.create_connection((sys.argv[1],int(sys.argv[2])),2);s.settimeout(1.5)
for line in sys.stdin:
 try:
  s.sendall(b'ping'); print('ok' if s.recv(4)==b'ping' else 'fail',flush=True)
 except OSError:
  print('fail',flush=True);break
'''


def probe(which, host, port, proto='tcp', expected='probe'):
    return ns(which, 'python3', '-c', PROBE, host, str(port), proto, expected,
              check=False) == 0


def stream(which, host, port):
    return subprocess.Popen(['ip', 'netns', 'exec', which, 'python3', '-u', '-c',
                             STREAM, host, str(port)], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)


def ping_stream(proc):
    proc.stdin.write('tick\n'); proc.stdin.flush()
    return proc.stdout.readline().strip() == 'ok'


def configure_client(which, private, address, server_key, tmp):
    ns(which, 'ip', 'link', 'del', 'client0', check=False)
    ns(which, 'ip', 'link', 'add', 'client0', 'type', 'wireguard')
    keyfile = tmp / (which + '.key')
    private_file(keyfile, private)
    ns(which, 'wg', 'set', 'client0', 'private-key', str(keyfile), 'peer', server_key,
       'endpoint', '172.24.0.1:65312', 'allowed-ips', '0.0.0.0/0',
       'persistent-keepalive', '25')
    ns(which, 'ip', 'addr', 'add', address + '/32', 'dev', 'client0')
    ns(which, 'ip', 'link', 'set', 'client0', 'up')
    ns(which, 'ip', 'route', 'replace', 'default', 'dev', 'client0')


def profile_private(path):
    for line in path.read_text().splitlines():
        if line.lower().startswith('privatekey'):
            return line.split('=', 1)[1].strip()
    raise RuntimeError('isolated client profile unavailable')


def inner(root, names):
    events = {}
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        events[name] = True

    m = manager.Manager(root=root)
    loader = importlib.machinery.SourceFileLoader('lab_gate', str(REPO / 'wg-remote-lan-route'))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    gate = importlib.util.module_from_spec(spec); loader.exec_module(gate)
    gate.NFT_RULESET = root / 'etc/nftables/omr.nft'
    gate.PEER_REGISTRY = m.registry
    gate.WG_CONFIG = m.config
    gate.STATE = m.gate_state
    gate.CONFIG = m.policy_dir / 'omr-admin-config.json'
    gate.LOCK = m.lock_path
    gate.MQVPN_CONFIG = root / 'etc/mqvpn/server.json'
    # Install the real helper in the isolated fixture and exercise the actual
    # Manager -> helper reconciliation, including its shared-lock contract and
    # routing table, rather than replacing reconciliation with a test callback.
    helper = root / 'usr/local/sbin/wg-remote-lan-route'
    helper.parent.mkdir(parents=True)
    shutil.copyfile(REPO / 'wg-remote-lan-route', helper)
    m.policy_dir.mkdir(parents=True)
    (m.policy_dir / 'omr-admin-config.json').write_text(json.dumps({'users':[{'openmptcprouter':{
        'vpnremoteip':'10.255.220.2', 'lanips':['192.168.100.0/24']}}]}))
    gate.set_lan_access(True)
    s, r, internet, a, b, legacy = (names[x] for x in ('server', 'router', 'internet', 'a', 'b', 'legacy'))
    server_pub = run(['wg', 'show', 'client-wg0', 'public-key'], capture=True)
    legacy_private = (root / 'legacy.key').read_text().strip()
    m.legacy_profile.parent.mkdir(parents=True)
    legacy_text = '[Interface]\nAddress = 10.255.246.2/24\nPrivateKey = '+legacy_private+'\n'
    m.legacy_profile.write_text(legacy_text)
    configure_client(legacy, legacy_private, '10.255.246.2', server_pub, root)
    sets = json.loads(run(['nft', '-j', 'list', 'set', 'inet', 'omr', 'wg_remote_peer_restrict_v4'], capture=True))
    entries = next(x['set'].get('elem', []) for x in sets['nftables'] if 'set' in x)
    check('freshly reloaded firewall starts with entire peer pool restricted',
          manager.nft_set_contains(entries, '10.255.246.2') and not probe(legacy, '192.168.100.5', 8080))
    m.initialize()
    check('legacy profile export validates its actual WireGuard key and IPv4 address', m.profile('legacy_2') == legacy_text)
    check('legacy GUI and globally enabled LAN remain reachable',
          probe(legacy, '10.255.220.2', 80) and probe(legacy, '192.168.100.5', 8080))
    alice, alice_profile = m.add('alice', endpoint='172.24.0.1:65312')
    m.legacy_profile.write_text(legacy_text.replace(legacy_private, profile_private(alice_profile)))
    try:
        m.profile('legacy_2')
        wrong_key_rejected = False
    except manager.ManagerError:
        wrong_key_rejected = True
    m.legacy_profile.write_text(legacy_text)
    check('legacy profile with a rotated mismatched private key is rejected', wrong_key_rejected)
    configure_client(a, profile_private(alice_profile), alice['ip'], server_pub, root)
    check('new client reaches router GUI by default', probe(a, '10.255.220.2', 80) and probe(a, '10.255.220.2', 443))
    alive = stream(a, '10.255.220.2', 80)
    check('first client existing session opens', ping_stream(alive))
    bob, bob_profile = m.add('bob', mode='full', endpoint='172.24.0.1:65312')
    configure_client(b, profile_private(bob_profile), bob['ip'], server_pub, root)
    check('adding another peer leaves existing connection alive', ping_stream(alive))
    alive.stdin.close(); alive.wait(timeout=4)
    check('second client reaches router GUI', probe(b, '10.255.220.2', 80))
    check('both new clients denied LAN by default', not probe(a, '192.168.100.5', 8080) and not probe(b, '192.168.100.5', 8080))
    nft = json.loads(run(['nft', '-j', 'list', 'set', 'inet', 'omr', 'wg_remote_peer_restrict_v4'], capture=True))
    restricted = next(x['set'].get('elem', []) for x in nft['nftables'] if 'set' in x)
    check('legacy INPUT remains exempt while new peers are restricted',
          not manager.nft_set_contains(restricted, '10.255.246.2') and
          manager.nft_set_contains(restricted, alice['ip']) and manager.nft_set_contains(restricted, bob['ip']))
    check('other VPN destination and router SSH denied', not probe(a, '10.255.220.3', 80) and not probe(a, '10.255.220.2', 22))
    check('new client denied VPS management port', not probe(a, '10.255.246.1', 65222))
    check('public Internet egress is SNATed to VPS address', probe(b, '1.1.1.1', 8080, expected='198.51.100.1'))
    check('public full tunnel DNS works', probe(b, '1.1.1.1', 53, proto='udp'))
    check('local VPS DNS response works', probe(b, '10.255.246.1', 53, proto='udp') and probe(b, '10.255.246.1', 53))
    check('private destinations cannot escape through WAN', not probe(b, '10.0.0.5', 8080))
    check('public DNAT and VPS service rules remain functional',
          probe(internet, '198.51.100.1', 8081) and probe(internet, '198.51.100.1', 12345))
    m.set_lan('alice', True)
    check('LAN grant applies to Alice but not Bob', probe(a, '192.168.100.5', 8080) and not probe(b, '192.168.100.5', 8080))
    rows = {p['name']: p for p in m.status()['peers']}
    check('status reflects live nft LAN grants and recent handshakes',
          rows['alice']['lan_firewall_open'] and not rows['bob']['lan_firewall_open'] and
          rows['alice']['last_handshake_age_seconds'] is not None and rows['alice']['rx_bytes'] > 0)
    open_lan = stream(a, '192.168.100.5', 8080)
    check('LAN connection established before revocation', ping_stream(open_lan))
    m.set_lan('alice', False)
    check('revoking LAN blocks an already established flow', not ping_stream(open_lan))
    open_lan.stdin.close(); open_lan.wait(timeout=4)
    check('revocation does not disrupt GUI', probe(a, '10.255.220.2', 80))
    m.set_lan('alice', True)
    gate.set_lan_access(False); m.reconcile()
    check('global master switch denies legacy and opted-in peers', not probe(legacy, '192.168.100.5', 8080) and not probe(a, '192.168.100.5', 8080))
    gate.set_lan_access(True); m.reconcile()
    check('global master restores only pre-existing per-peer grants', probe(a, '192.168.100.5', 8080) and probe(legacy, '192.168.100.5', 8080) and not probe(b, '192.168.100.5', 8080))
    m.disable('alice', remove=True)
    carol, carol_profile = m.add('carol', ip=alice['ip'], endpoint='172.24.0.1:65312')
    configure_client(a, profile_private(carol_profile), carol['ip'], server_pub, root)
    check('reused address has no inherited LAN grant', probe(a, '10.255.220.2', 80) and not probe(a, '192.168.100.5', 8080))
    check('removing a peer does not drop another', probe(b, '10.255.220.2', 80) and probe(b, '1.1.1.1', 8080, expected='198.51.100.1'))
    # Emulate a process failure immediately after WireGuard accepted a new
    # public key but before the manager commits the active state.
    original_command = m.command
    def fail_after_add(args, **kwargs):
        result = original_command(args, **kwargs)
        if args[:3] == ['wg', 'set', 'client-wg0'] and 'allowed-ips' in args:
            raise manager.ManagerError('injected activation interruption')
        return result
    m.command = fail_after_add
    try:
        try:
            m.add('interrupted', endpoint='172.24.0.1:65312')
            raise AssertionError('interrupted operation unexpectedly succeeded')
        except manager.ManagerError:
            pass
    finally:
        m.command = original_command
    pending = next(p for p in m.load()['peers'] if p['name'] == 'interrupted')
    check('interrupted address remains reserved with LAN closed',
          pending['state'] == 'adding' and pending['ip'] not in manager.peer_policy(m.registry, m.config)[0])
    m.recover()
    pending = next(p for p in m.load()['peers'] if p['name'] == 'interrupted')
    try:
        m.add('must_not_reuse', ip=pending['ip'], endpoint='172.24.0.1:65312')
        reused = True
    except manager.ManagerError:
        reused = False
    check('recovery disables incomplete peer and prevents address reuse', pending['state'] == 'disabled' and not reused)
    check('unrelated peer stays connected through recovery', probe(b, '10.255.220.2', 80))
    def global_gate(action=None):
        original_argv = sys.argv
        sys.argv = ['wg-remote-lan-route', '--config', str(gate.CONFIG)]
        if action is not None:
            sys.argv += ['--lan-access', action]
        try:
            return gate.main()
        finally:
            sys.argv = original_argv
    m.set_lan('carol', True)
    ongoing = stream(a, '192.168.100.5', 8080)
    check('LAN session starts before old source file refresh', ping_stream(ongoing))
    gate.NFT_RULESET.write_text('# old file without per-peer set definitions\n')
    data = m.load()
    next(p for p in data['peers'] if p['name'] == 'carol')['lan'] = False
    m.persist(data)  # Simulate an interruption after a deny was persisted.
    check('timer refresh recognizes live per-peer sets despite old disk file', global_gate() == 0)
    check('old-source refresh revokes established flow while global LAN stays enabled',
          not ping_stream(ongoing) and m.gate_state.exists() and probe(legacy, '192.168.100.5', 8080))
    ongoing.stdin.close(); ongoing.wait(timeout=4)
    gate.NFT_RULESET.write_text((REPO / 'nftables/omr.nft').read_text())
    m.set_lan('carol', True)
    check('LAN is open before testing a lost ruleset file', probe(a, '192.168.100.5', 8080))
    ongoing = stream(a, '192.168.100.5', 8080)
    check('LAN connection remains established before missing-file deny', ping_stream(ongoing))
    gate.NFT_RULESET.unlink()
    check('global deny succeeds with missing disk rules only after live nft revoke',
          global_gate('deny') == 0 and not m.gate_state.exists())
    check('missing-file global deny stops established LAN flow with main route still present',
          not ping_stream(ongoing) and '192.168.100.0/24' in run(['ip','-4','route','show','table','main'],capture=True))
    ongoing.stdin.close(); ongoing.wait(timeout=4)
    check('global deny with missing rules retains GUI rescue', probe(a, '10.255.220.2', 80))
    gate.NFT_RULESET.write_text((REPO / 'nftables/omr.nft').read_text())
    check('global gate can be explicitly restored', global_gate('allow') == 0)
    ongoing = stream(a, '192.168.100.5', 8080)
    check('LAN connection established before missing-file per-peer revoke', ping_stream(ongoing))
    gate.NFT_RULESET.unlink()
    try:
        m.set_lan('carol', False)
        raise AssertionError('missing-file per-peer revoke unexpectedly succeeded')
    except manager.ManagerError:
        pass
    row = next(p for p in m.load()['peers'] if p['name'] == 'carol')
    check('missing-file per-peer revoke quarantines key and ends the established flow',
          row['state'] == 'quarantine' and not ping_stream(ongoing))
    ongoing.stdin.close(); ongoing.wait(timeout=4)
    check('quarantining one client leaves another peer operational', probe(b, '10.255.220.2', 80))
    print(json.dumps({'passed': len(events), 'checks': events, 'lab': 'real WireGuard and full shipped nftables rules; simulated OMR tunnel'}, sort_keys=True))


def outer(report_path=None):
    if os.geteuid() or any(not shutil.which(x) for x in ('ip', 'nft', 'wg', 'python3')):
        raise RuntimeError('requires root and ip, nft, wg and python3')
    sources = ('omr_wg_manager.py', 'omr-wg-manager', 'wg-remote-lan-route',
               'nftables/omr.nft', 'nftables/omr-vars.nft', 'debian9-x86_64.sh',
               'tests/test_omr_wg_manager.py', 'tests/run_omr_wg_netns.py')
    digests = {path:hashlib.sha256((REPO/path).read_bytes()).hexdigest() for path in sources}
    token = secrets.token_hex(3)
    names = {role:'omrwg' + token + suffix for role, suffix in
             [('server','s'),('router','r'),('internet','i'),('a','a'),('b','b'),('legacy','l')]}
    created, processes, host_links = [], [], []
    with tempfile.TemporaryDirectory(prefix='omr-wg-netns-') as tmpname:
        root = Path(tmpname)
        try:
            for name in names.values():
                run(['ip', 'netns', 'add', name]); created.append(name)
                ns(name, 'ip', 'link', 'set', 'lo', 'up')
            def pair(left, right, ldev, rdev, index):
                x, y = 'w' + token + str(index) + 'a', 'w' + token + str(index) + 'b'
                host_links.extend([x, y]); run(['ip', 'link', 'add', x, 'type', 'veth', 'peer', 'name', y])
                run(['ip', 'link', 'set', x, 'netns', names[left]])
                run(['ip', 'link', 'set', y, 'netns', names[right]])
                ns(names[left], 'ip', 'link', 'set', x, 'name', ldev)
                ns(names[right], 'ip', 'link', 'set', y, 'name', rdev)
                ns(names[left], 'ip', 'link', 'set', ldev, 'up')
                ns(names[right], 'ip', 'link', 'set', rdev, 'up')
            s, r, internet = (names[x] for x in ('server', 'router', 'internet'))
            ns(s, 'ip', 'link', 'add', 'bridge0', 'type', 'bridge')
            ns(s, 'ip', 'addr', 'add', '172.24.0.1/24', 'dev', 'bridge0')
            ns(s, 'ip', 'link', 'set', 'bridge0', 'up')
            for index, role in enumerate(('legacy', 'a', 'b'), 1):
                pair('server', role, 'brport' + str(index), 'outside0', index)
                ns(s, 'ip', 'link', 'set', 'brport' + str(index), 'master', 'bridge0')
                ns(names[role], 'ip', 'addr', 'add', '172.24.0.' + str(index + 1) + '/24', 'dev', 'outside0')
            pair('server', 'router', 'tun0', 'router0', 4)
            ns(s, 'ip', 'addr', 'add', '10.255.220.1/24', 'dev', 'tun0')
            ns(r, 'ip', 'addr', 'add', '10.255.220.2/24', 'dev', 'router0')
            ns(r, 'ip', 'addr', 'add', '10.255.220.3/24', 'dev', 'router0')
            ns(r, 'ip', 'addr', 'add', '192.168.100.5/32', 'dev', 'lo')
            ns(s, 'ip', 'route', 'add', '192.168.100.0/24', 'via', '10.255.220.2', 'dev', 'tun0')
            pair('server', 'internet', 'wan0', 'inet0', 5)
            ns(s, 'ip', 'addr', 'add', '198.51.100.1/24', 'dev', 'wan0')
            ns(internet, 'ip', 'addr', 'add', '198.51.100.2/24', 'dev', 'inet0')
            ns(internet, 'ip', 'addr', 'add', '1.1.1.1/32', 'dev', 'lo')
            ns(internet, 'ip', 'addr', 'add', '10.0.0.5/32', 'dev', 'lo')
            ns(s, 'ip', 'route', 'add', '1.1.1.1/32', 'via', '198.51.100.2', 'dev', 'wan0')
            ns(s, 'ip', 'route', 'add', '10.0.0.5/32', 'via', '198.51.100.2', 'dev', 'wan0')
            ns(r, 'ip', 'route', 'add', '198.51.100.0/24', 'via', '10.255.220.1', 'dev', 'router0')
            ns(s, 'sysctl', '-q', '-w', 'net.ipv4.ip_forward=1')
            server_private, server_public = keypair(); legacy_private, legacy_public = keypair()
            private_file(root / 'server.key', server_private); private_file(root / 'legacy.key', legacy_private)
            ns(s, 'ip', 'link', 'add', 'client-wg0', 'type', 'wireguard')
            ns(s, 'wg', 'set', 'client-wg0', 'private-key', str(root / 'server.key'), 'listen-port', '65312',
               'peer', legacy_public, 'allowed-ips', '10.255.246.2/32')
            ns(s, 'ip', 'addr', 'add', '10.255.246.1/24', 'dev', 'client-wg0')
            ns(s, 'ip', 'link', 'set', 'client-wg0', 'up')
            config = root / 'etc/wireguard/client-wg0.conf'; config.parent.mkdir(parents=True)
            config.write_text('[Interface]\nAddress = 10.255.246.1/24\nPrivateKey = ' + server_private + '\nListenPort = 65312\nSaveConfig = true\n\n[Peer]\nPublicKey = ' + legacy_public + '\nAllowedIPs = 10.255.246.2/32\n')
            config.chmod(0o600)
            rulesdir = root / 'etc/nftables'; rulesdir.mkdir(parents=True)
            original = (REPO / 'nftables/omr.nft').read_text()
            (rulesdir / 'omr.nft').write_text(original)
            variables = (REPO / 'nftables/omr-vars.nft').read_text().replace('define NET_IFACE = eth0', 'define NET_IFACE = wan0')
            combined = root / 'rules.nft'; combined.write_text(variables + '\n' + original)
            ns(s, 'nft', '-f', str(combined))
            # Exercise existing dynamic public forward and VPS-service paths.
            ns(s, 'nft', 'add', 'rule', 'inet', 'omr', 'user_dnat', 'iifname', 'wan0',
               'tcp', 'dport', '8081', 'dnat', 'ip', 'to', '10.255.220.2:80')
            ns(s, 'nft', 'add', 'rule', 'inet', 'omr', 'user_accept', 'tcp', 'dport', '12345', 'accept')
            def serve(which, host, port, proto='tcp', mode='echo'):
                p = subprocess.Popen(['ip', 'netns', 'exec', which, 'python3', '-u', '-c', SERVER,
                                      host, str(port), proto, mode], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                processes.append(p)
            serve(r, '0.0.0.0', 80); serve(r, '0.0.0.0', 443); serve(r, '0.0.0.0', 22)
            serve(r, '192.168.100.5', 8080)
            serve(internet, '1.1.1.1', 8080, mode='reflect')
            serve(internet, '1.1.1.1', 53, proto='udp')
            serve(internet, '10.0.0.5', 8080)
            serve(s, '10.255.246.1', 53, proto='udp'); serve(s, '10.255.246.1', 53); serve(s, '10.255.246.1', 65222)
            serve(s, '198.51.100.1', 12345)
            time.sleep(0.5)
            if any(p.poll() is not None for p in processes):
                raise RuntimeError('isolated test service failed to start')
            result = subprocess.run(['ip', 'netns', 'exec', s, sys.executable, str(Path(__file__).resolve()),
                                     '--inner', str(root), json.dumps(names)], text=True, capture_output=True,
                                    timeout=90)
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or 'isolated packet assertions failed')
            report = json.loads(result.stdout)
            after = {path:hashlib.sha256((REPO/path).read_bytes()).hexdigest() for path in sources}
            if after != digests:
                raise RuntimeError('source changed while the isolated lab was running')
            report['tested_at_utc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
            report['source_sha256'] = digests
            report['scope'] = 'isolated WSL/Linux namespaces; simulated OMR router and public endpoint; no installer, reboot, real MQVPN or production host'
            if report_path:
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
            print(json.dumps(report, sort_keys=True))
        finally:
            for p in processes:
                p.terminate()
            for p in processes:
                try: p.wait(timeout=2)
                except subprocess.TimeoutExpired: p.kill(); p.wait()
            for name in reversed(created):
                run(['ip', 'netns', 'del', name], check=False)
            # Only deterministic names generated by this test are eligible.
            for link in host_links:
                run(['ip', 'link', 'del', link], check=False)


if __name__ == '__main__':
    try:
        if len(sys.argv) == 4 and sys.argv[1] == '--inner':
            inner(Path(sys.argv[2]), json.loads(sys.argv[3]))
        elif len(sys.argv) == 3 and sys.argv[1] == '--report':
            outer(Path(sys.argv[2]))
        elif len(sys.argv) == 1:
            outer()
        else:
            raise RuntimeError('usage: run_omr_wg_netns.py [--report PATH]')
    except Exception as exc:
        print(json.dumps({'result':'FAIL', 'reason':str(exc)}), file=sys.stderr)
        sys.exit(1)
