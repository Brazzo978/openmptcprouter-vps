import json
import subprocess
import sys

import pytest

from conftest import omr_admin

_REAL_POPEN = subprocess.Popen


def _line(unit, message, timestamp, priority=6, **extra):
    return json.dumps({
        '_SYSTEMD_UNIT': unit,
        '__REALTIME_TIMESTAMP': str(timestamp),
        'PRIORITY': str(priority),
        'MESSAGE': message,
        **extra,
    }).encode() + b'\n'


def test_route_requires_authentication(unauth_client, monkeypatch):
    monkeypatch.setattr(omr_admin, '_diagnostic_journal',
                        lambda limit: (_ for _ in ()).throw(AssertionError('read')))
    response = unauth_client.get('/diagnostic/logs')
    assert response.status_code == 403


def test_regular_router_user_gets_normalized_redacted_entries(user_client, monkeypatch):
    output = b''.join([
        _line('mqvpn.service',
              '[ERR] xquic close err:0x0 password=alpha token="beta" '
              'https://alice:gamma@example.invalid/path', 1700000002000000, 3,
              SECRET='metadata-must-never-escape'),
        b'{bad json}\n',
        _line('xray.service',
              'Authorization: Bearer opaque-value {"auth":{"private_key":"delta"}}',
              1700000001000000, 4),
        _line('unrelated.service', 'message that must be excluded',
              1700000003000000),
    ])
    calls = []
    monkeypatch.setattr(omr_admin, '_diagnostic_journal',
                        lambda limit: calls.append(limit) or output)
    response = user_client.get('/diagnostic/logs')
    assert response.status_code == 200
    assert calls == [300]
    entries = response.json()['entries']
    assert len(entries) == 2
    assert entries[0]['timestamp'] == 1700000002
    assert entries[0]['scope'] == 'vps'
    assert entries[0]['source'] == 'mqvpn'
    assert entries[0]['component'] == 'vpn'
    assert entries[0]['severity'] == 'info'
    assert entries[1]['severity'] == 'warning'
    assert set(entries[0]) == {
        'timestamp', 'scope', 'source', 'component', 'severity', 'message'
    }
    serialized = json.dumps(response.json())
    for secret in ('alpha', 'beta', 'gamma', 'opaque-value', 'delta',
                   'metadata-must-never-escape'):
        assert secret not in serialized
    assert 'https://[REDACTED]@example.invalid/path' in serialized


def test_mqvpn_levels_and_service_allowlist():
    for tag, severity in [('DBG', 'debug'), ('INF', 'info'),
                          ('WRN', 'warning'), ('ERR', 'error')]:
        entry = omr_admin._diagnostic_entry({
            '_SYSTEMD_UNIT': 'mqvpn.service',
            '__REALTIME_TIMESTAMP': '1700000000000000',
            'PRIORITY': 6,
            'MESSAGE': f'[{tag}] event',
        })
        assert entry['severity'] == severity
    assert omr_admin._diagnostic_entry({
        '_SYSTEMD_UNIT': 'unrelated.service',
        '__REALTIME_TIMESTAMP': '1700000000000000',
        'MESSAGE': 'no',
    }) is None
    assert omr_admin._diagnostic_source('wg-quick@wg0.service') == (
        'wireguard', 'vpn'
    )
    expected_sources = {
        'mqvpn-server.service': ('mqvpn', 'vpn'),
        'dsvpn-server@dsvpn1.service': ('dsvpn', 'vpn'),
        'openvpn@tun0.service': ('openvpn', 'vpn'),
        'openvpn-server@server.service': ('openvpn', 'vpn'),
        'shadowsocks-libev-server@user0.service': ('shadowsocks', 'proxy'),
        'shadowsocks-libev-manager@manager.service': ('shadowsocks', 'proxy'),
        'shadowsocks-go.service': ('shadowsocks', 'proxy'),
    }
    for unit, expected in expected_sources.items():
        assert omr_admin._diagnostic_source(unit) == expected


def test_limits_are_validated_and_journal_error_is_generic(user_client, monkeypatch):
    calls = []
    monkeypatch.setattr(omr_admin, '_diagnostic_journal',
                        lambda limit: calls.append(limit) or b'')
    for limit in ('0', '1001', 'nope'):
        assert user_client.get('/diagnostic/logs?limit=' + limit).status_code == 422
    assert calls == []
    assert user_client.get('/diagnostic/logs?limit=1000').json() == {'entries': []}
    assert calls == [1000]
    def fail(limit):
        raise OSError('secret stderr contents')
    monkeypatch.setattr(omr_admin, '_diagnostic_journal', fail)
    response = user_client.get('/diagnostic/logs')
    assert response.status_code == 200
    assert response.json() == {
        'entries': [], 'error': 'VPS journal unavailable'
    }
    assert 'secret stderr contents' not in response.text


def test_redaction_covers_nested_and_prefixed_secret_fields():
    message = ('{"outer":{"user_password":"alpha","api_token":"bravo",'
               '"user":{"ss_key":"charlie","v2ray_uuid":"delta",'
               '"private_key":"echo"}}} '
               'preshared_key=foxtrot')
    sanitized = omr_admin._diagnostic_redact(message)
    for secret in ('alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot'):
        assert secret not in sanitized
    assert sanitized.count('[REDACTED]') == 6


def test_redaction_covers_auth_schemes_url_and_private_block():
    samples = (
        ('Authorization: Basic YWxpY2U6c2VjcmV0', 'YWxpY2U6c2VjcmV0'),
        ('Authorization: Bearer opaque.value', 'opaque.value'),
        ('Authorization: Digest username="alice", response="digest-secret"',
         'digest-secret'),
        ('{"Authorization":"Basic Ym9iOnBhc3M="}', 'Ym9iOnBhc3M='),
        ('Basic c3RhbmRhbG9uZQ==', 'c3RhbmRhbG9uZQ=='),
        ('socks5://user:uri-password@example.invalid/path', 'uri-password'),
        ('-----BEGIN PRIVATE KEY-----pem-secret-----END PRIVATE KEY-----',
         'pem-secret'),
    )
    for message, secret in samples:
        assert secret not in omr_admin._diagnostic_redact(message)
    assert 'socks5://[REDACTED]@example.invalid/path' == (
        omr_admin._diagnostic_redact(
            'socks5://user:uri-password@example.invalid/path'
        )
    )


@pytest.fixture
def journal_child(monkeypatch):
    # Run a tiny Python child in place of journalctl; never touch the host journal.
    spawned = []

    def use_script(script):
        def start(command, **kwargs):
            process = _REAL_POPEN([sys.executable, '-c', script], **kwargs)
            spawned.append((command, kwargs, process))
            return process
        monkeypatch.setattr(omr_admin.subprocess, 'Popen', start)
        return spawned

    yield use_script

    # A failed assertion must not leave a sleeping child behind.
    for _, _, process in spawned:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=2)


@pytest.mark.skipif(sys.platform == 'win32', reason='pipe selector requires Linux')
def test_bounded_reader_uses_only_fixed_journal_units(journal_child):
    spawned = journal_child('import os; os.write(1, bytes([123, 125, 10]))')
    assert omr_admin._diagnostic_journal(7) == b'{}\n'
    command, kwargs, process = spawned[0]
    assert command[:7] == [
        'journalctl', '--no-pager', '--quiet', '--output=json',
        '--output-fields=__REALTIME_TIMESTAMP,_SYSTEMD_UNIT,PRIORITY,MESSAGE',
        '--reverse', '--lines=7'
    ]
    assert command[7:] == [
        '--unit=' + unit for unit in omr_admin._DIAGNOSTIC_UNITS
    ]
    assert kwargs['stdin'] == subprocess.DEVNULL
    assert kwargs['stderr'] == subprocess.DEVNULL
    assert kwargs['stdout'] == subprocess.PIPE
    assert process.poll() == 0


@pytest.mark.skipif(sys.platform == 'win32', reason='pipe selector requires Linux')
def test_bounded_reader_kills_child_when_output_exceeds_cap(journal_child, monkeypatch):
    spawned = journal_child(
        "import os,time; os.write(1,b'x'*8192); time.sleep(30)"
    )
    monkeypatch.setattr(omr_admin, '_DIAGNOSTIC_MAX_BYTES', 1024)
    monkeypatch.setattr(omr_admin, '_DIAGNOSTIC_TIMEOUT', 2.0)
    with pytest.raises(ValueError, match='too large'):
        omr_admin._diagnostic_journal(1)
    assert len(spawned) == 1
    assert spawned[0][2].poll() is not None


@pytest.mark.skipif(sys.platform == 'win32', reason='pipe selector requires Linux')
def test_bounded_reader_kills_silent_child_on_timeout(journal_child, monkeypatch):
    spawned = journal_child('import time; time.sleep(30)')
    monkeypatch.setattr(omr_admin, '_DIAGNOSTIC_TIMEOUT', 0.05)
    with pytest.raises(TimeoutError, match='timeout'):
        omr_admin._diagnostic_journal(1)
    assert len(spawned) == 1
    assert spawned[0][2].poll() is not None
