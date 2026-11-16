import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

MODULE = Path(__file__).resolve().parents[1] / 'admin' / 'omr_dashboard.py'
spec = importlib.util.spec_from_file_location('omr_dashboard', MODULE)
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


def put(root, path, value):
    file = root / path.lstrip('/')
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(value if isinstance(value, str) else json.dumps(value))


def test_history_isolated_redaction_and_unknown(tmp_path):
    put(tmp_path, '/etc/openmptcprouter-vps-admin/omr-admin-config.json', {'users': [{'router': {'vpn': 'mqvpn', 'proxy': 'xray', 'vpnremoteip': '10.1.2.3', 'lanips': ['192.168.5.0/24'], 'password': 'very-secret'}, 'bad name': {'password': 'very-secret'}}]})
    put(tmp_path, '/etc/mqvpn/server.json', {'users': [{'name': 'router', 'key': 'mq-secret'}], 'scheduler': 'wlb', 'cc': 'bbr2', 'auth_key': 'auth-secret'})
    now = [1000]
    connection = [{'user': 'router', 'secret': 'session-secret'}]
    runner = lambda *a, **k: SimpleNamespace(returncode=1, stdout='')
    collector = d.Collector(tmp_path, runner, lambda: now[0], control=lambda: {'ok': True, 'clients': connection})
    assert d.note_contact('router', '/config?token=route-secret', root=tmp_path, clock=lambda: now[0])
    first = collector.collect()
    assert first['clients'][0]['state'] == 'connected'
    assert first['clients'][0]['last_seen_at'] == 1000
    assert first['clients'][0]['last_connected_at'] == 1000
    now[0] += 15
    connection.clear()
    second = collector.collect()
    assert second['clients'][0]['last_disconnected_at'] == 1015
    now[0] += 15
    collector.control = lambda: None
    third = collector.collect()
    assert third['clients'][0]['state'] == 'unknown'
    assert third['clients'][0]['last_disconnected_at'] == 1015
    for path in (tmp_path / 'run/omr-dashboard/snapshot.json', tmp_path / 'var/lib/omr-dashboard/history.json'):
        text = path.read_text()
        for secret in ('very-secret', 'mq-secret', 'auth-secret', 'session-secret', 'route-secret'):
            assert secret not in text
    assert not d.note_contact('bad name', root=tmp_path, clock=lambda: now[0])
    assert 'collector snapshot stale' in d.read_snapshot(tmp_path, lambda: 2000)['warnings']


def test_contact_is_not_tunnel_evidence(tmp_path):
    put(tmp_path, '/etc/openmptcprouter-vps-admin/omr-admin-config.json', {'users': [{'router': {'vpn': 'mqvpn'}}]})
    d.note_contact('router', root=tmp_path, clock=lambda: 10)
    collector = d.Collector(tmp_path, lambda *a, **k: SimpleNamespace(returncode=1, stdout=''), lambda: 10, control=lambda: None)
    client = collector.collect()['clients'][0]
    assert client['state'] == 'unknown'
    assert client['last_seen_at'] == 10
    assert client['last_connected_at'] is None


def test_missing_collector_cannot_be_presented_as_live_or_zero_clients(tmp_path):
    result=d.read_snapshot(tmp_path, lambda:1000)
    assert result['generated_at'] is None
    assert result['collection_state'] == 'unavailable'
    assert result['clients'] is None
    assert result['wireguard']['peers'] is None


def test_disconnect_observed_after_gap_is_explicit(tmp_path):
    put(tmp_path, '/etc/openmptcprouter-vps-admin/omr-admin-config.json', {'users':[{'router':{'vpn':'mqvpn'}}]})
    now=[1000]
    collector=d.Collector(tmp_path,lambda *a,**kw:SimpleNamespace(returncode=1,stdout=''),lambda:now[0],control=lambda:{'ok':True,'clients':[{'user':'router'}]})
    collector.collect()
    now[0]=1015
    collector.control=lambda:None
    collector.collect()
    now[0]=1200
    collector.control=lambda:{'ok':True,'clients':[]}
    result=collector.collect()
    assert result['clients'][0]['last_disconnected_at']==1200
    assert result['clients'][0]['last_transition_after_gap'] is True
    assert result['events'][-1]['after_observation_gap'] is True


def test_wireguard_gate_and_firewall_actual_state(tmp_path):
    key = 'A' * 43 + '='
    put(tmp_path, '/etc/openmptcprouter-vps-admin/wg-remote-manager/peers.json', {'version': 1, 'peers': [{'name': 'phone', 'public_key': key, 'ip': '10.255.246.2', 'state': 'active', 'lan': True}]})
    put(tmp_path, '/etc/openmptcprouter-vps-admin/wg-remote-lan-access.enabled', 'allow')
    def run(argv, **kwargs):
        if argv[:3] == ['wg', 'show', 'client-wg0']:
            data = {'allowed-ips': '10.255.246.2/32', 'latest-handshakes': '950', 'transfer': '123 456'}
            return SimpleNamespace(returncode=0, stdout=key + ' ' + data[argv[3]] + '\n')
        if argv[0] == 'nft':
            elements = [{'prefix': {'addr': '10.255.246.2', 'len': 32}}] if argv[-1] == 'wg_remote_peer_lan_v4' else ['192.168.1.0/24']
            return SimpleNamespace(returncode=0, stdout=json.dumps({'nftables': [{'set': {'name': argv[-1], 'elem': elements}}]}))
        return SimpleNamespace(returncode=1, stdout='')
    collector = d.Collector(tmp_path, run, lambda: 1000, control=lambda: None)
    result = collector.collect()['wireguard']
    assert result['summary']['global_lan_gate'] is True
    peer = result['peers'][0]
    assert peer['connected'] and peer['last_handshake_at'] == 950
    assert peer['rx_bytes'] == 123 and peer['tx_bytes'] == 456
    assert peer['lan_access_requested'] and peer['lan_access_effective']
    assert key not in json.dumps(result)
    (tmp_path / 'etc/openmptcprouter-vps-admin/wg-remote-lan-access.enabled').unlink()
    result = collector.collect()['wireguard']
    assert result['summary']['global_lan_gate'] is False
    # Expose stale firewall grants even when the persisted gate is disabled.
    assert result['peers'][0]['lan_access_effective'] is True


def test_only_fixed_read_commands_and_timeouts(tmp_path):
    calls = []
    def run(argv, **kw):
        calls.append((argv, kw))
        return SimpleNamespace(returncode=1, stdout='private-output')
    d.Collector(tmp_path, run, lambda: 1000, control=lambda: None).collect()
    assert calls
    assert all(c[0][0] in ('wg', 'nft', 'systemctl', 'ip', 'ss') and 0 < c[1]['timeout'] <= 1 for c in calls)
    assert all('shell' not in c[1] for c in calls)
    assert 'private-output' not in (tmp_path / 'run/omr-dashboard/snapshot.json').read_text()


def test_live_paths_interface_and_system_scope(tmp_path):
    put(tmp_path, '/etc/openmptcprouter-vps-admin/omr-admin-config.json', {'users': [{'admin': {'permissions': 'admin', 'password': 'secret'}, 'openmptcprouter': {'vpn': 'mqvpn', 'userid': 0}}]})
    put(tmp_path, '/etc/mqvpn/server.json', {'tun_name': 'mqvpn0', 'scheduler': 'wlb', 'reorder': {'enabled': 'auto', 'max_wait_ms': 30, 'secret': 'secret'}, 'path_policy': [{'user': 'openmptcprouter', 'iface': 'wan', 'weight': 5}]})
    put(tmp_path, '/proc/meminfo', 'MemTotal: 1000 kB\nMemAvailable: 400 kB\n')
    put(tmp_path, '/var/lib/omr-profiles/transaction.json', {'state': 'pending', 'transaction': 'secret'})
    def run(argv, **kwargs):
        if argv[0] == 'ip':
            return SimpleNamespace(returncode=0, stdout=json.dumps([{'ifname': 'mqvpn0', 'mtu': 1400, 'operstate': 'UP', 'addr_info': [{'local': '10.255.220.1'}], 'stats64': {'rx': {'bytes': 11}, 'tx': {'bytes': 22}}}]))
        return SimpleNamespace(returncode=1, stdout='')
    status = {'ok': True, 'clients': [{'user': 'openmptcprouter', 'endpoint': 'secret', 'paths': [{'path_id': 2, 'srtt_ms': 20, 'pkt_lost': 3, 'cwnd': 100, 'secret': 'secret'}]}]}
    data = d.Collector(tmp_path, run, lambda: 1000, control=lambda: status).collect()
    assert len(data['clients']) == 1
    client = data['clients'][0]
    assert client['tunnel']['interface'] == 'mqvpn0' and client['tunnel']['mtu'] == 1400
    assert client['tunnel']['interface_counters'] == {'rx_bytes': 11, 'tx_bytes': 22}
    assert client['tunnel']['paths'][0]['srtt_ms'] == 20
    assert client['tunnel']['settings']['path_policy'][0]['weight'] == 5
    assert client['settings']['profile_state'] == 'pending'
    assert 'VPS' in client['mptcp']['source']
    assert data['server']['memory']['used_bytes'] == 600 * 1024
    assert 'secret' not in json.dumps(data)


def test_malformed_fields_do_not_stop_collector(tmp_path):
    put(tmp_path, '/etc/openmptcprouter-vps-admin/omr-admin-config.json', {'users': [{'router': {'vpn': [], 'proxy': {}, 'lanips': [None, {}, '192.168.10.0/24']}}]})
    put(tmp_path, '/etc/mqvpn/server.json', {'users': ['bad', {}, {'name': []}], 'reorder': {'enabled': []}, 'path_policy': [{'user': 'router', 'iface': []}]})
    runner = lambda *a, **k: SimpleNamespace(returncode=1, stdout='')
    result = d.Collector(tmp_path, runner, lambda: 10, control=lambda: {'ok': True, 'clients': [None, {'user': []}]}).collect()
    assert result['clients'][0]['tunnel']['configured'] is None
    assert result['clients'][0]['lan_subnets'] == ['192.168.10.0/24']


def test_tcp_observations_require_unique_port_and_never_persist_addresses(tmp_path):
    put(tmp_path, '/etc/openmptcprouter-vps-admin/omr-admin-config.json', {'users': [{'one': {'vpn': 'glorytun_tcp', 'vpn_port': 65001, 'proxy': 'shadowsocks', 'shadowsocks_port': 65101}, 'two': {'proxy': 'shadowsocks', 'shadowsocks_port': 65102}, 'three': {'proxy': 'shadowsocks', 'shadowsocks_port': 65102}}]})
    def run(argv, **kwargs):
        if argv[0] == 'ss': return SimpleNamespace(returncode=0, stdout='0 0 10.1.1.1:65001 203.0.113.55:45678\n0 0 10.1.1.1:65101 203.0.113.55:56789\n')
        return SimpleNamespace(returncode=1, stdout='')
    data = d.Collector(tmp_path, run, lambda: 1000, control=lambda: None).collect()
    clients = {c['username']: c for c in data['clients']}
    assert clients['one']['tunnel']['tcp_connections'] == 1
    assert clients['one']['state'] == 'unknown'
    assert clients['one']['proxy']['tcp_connections'] == 1
    assert clients['two']['proxy']['tcp_connections'] is None
    assert clients['three']['proxy']['tcp_connections'] is None
    assert '203.0.113.55' not in json.dumps(data)


def test_malformed_cached_snapshot_returns_unavailable(tmp_path):
    put(tmp_path, '/run/omr-dashboard/snapshot.json', {'schema_version': 1, 'generated_at': 10, 'warnings': 'not a list'})
    assert d.read_snapshot(tmp_path, lambda: 100)['warnings'] == ['collector snapshot unavailable']
