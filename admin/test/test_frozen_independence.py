"""Frozen VPS metadata must be local or explicitly configured."""
import copy
import io
import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from conftest import MOCK_CONFIG, _mock_open, omr_admin


MARKER = "/etc/omr-vps-3k-frozen.json"
SERVER = Path(__file__).resolve().parents[2]


def _no_external_metadata(url, *args, **kwargs):
    if url.startswith(("http://127.0.0.1", "https://127.0.0.1")):
        response = MagicMock()
        response.text = ""
        response.status_code = 200
        response.json.return_value = {}
        return response
    raise AssertionError("frozen VPS tried an external metadata endpoint: " + url)


def test_frozen_config_uses_local_metadata_without_http(user_client, monkeypatch):
    monkeypatch.setattr(omr_admin.path, "isfile", lambda filename: filename == MARKER)
    monkeypatch.setattr(omr_admin, "_iface_global_addr",
                        lambda iface, family: "192.0.2.10" if family == 4 else "")
    monkeypatch.setattr(omr_admin.socket, "gethostname", lambda: "vps-local")
    monkeypatch.setattr(omr_admin.requests, "get", _no_external_metadata)
    response = user_client.get("/config")
    assert response.status_code == 200
    assert response.json()["network"]["ipv4"] == "192.0.2.10"
    assert response.json()["network"]["domain"] == "vps-local"


def test_frozen_config_keeps_explicit_nat_metadata(user_client, monkeypatch):
    config = copy.deepcopy(MOCK_CONFIG)
    config.update(ipv4="198.51.100.42", hostname="vps.example.net")
    monkeypatch.setattr(omr_admin, "read_omr_config", lambda: copy.deepcopy(config))
    monkeypatch.setattr(omr_admin.path, "isfile", lambda filename: filename == MARKER)
    monkeypatch.setattr(omr_admin.requests, "get", _no_external_metadata)
    response = user_client.get("/config")
    assert response.status_code == 200
    assert response.json()["network"]["ipv4"] == "198.51.100.42"
    assert response.json()["network"]["domain"] == "vps.example.net"


def test_frozen_shadowsocks_uses_local_hostname_without_http(user_client, monkeypatch):
    manager = json.dumps({"timeout": 600, "verbose": 0, "port_key": {"65101": "old-key"}})
    manager_path = "/etc/shadowsocks-libev/manager.json"
    def fake_open(path, mode="r", *args, **kwargs):
        if str(path) == manager_path:
            if "w" in str(mode):
                return io.StringIO()
            if "b" in str(mode):
                return io.BytesIO(manager.encode())
            return io.StringIO(manager)
        return _mock_open(path, mode, *args, **kwargs)
    monkeypatch.setattr(omr_admin.path, "isfile",
                        lambda filename: filename in (MARKER, manager_path))
    monkeypatch.setattr(omr_admin.socket, "gethostname", lambda: "vps-local")
    monkeypatch.setattr(omr_admin.requests, "get", _no_external_metadata)
    payload = {
        "port": 65101, "method": "chacha20-ietf-poly1305", "fast_open": False,
        "reuse_port": False, "no_delay": False, "mptcp": True, "obfs": False,
        "obfs_plugin": "obfs", "obfs_type": "http", "key": "testkey",
    }
    with patch("builtins.open", side_effect=fake_open):
        response = user_client.post("/shadowsocks", json=payload)
    assert response.status_code == 200
    assert response.json()["result"] != "warning"


def test_installer_guards_upstream_before_apt():
    script = (SERVER / "debian9-x86_64.sh").read_text()
    frozen_branch = script.index('if [ "$OMR_3K_FROZEN" = "yes" ]; then')
    old_metadata = script.index("http://hostname.openmptcprouter.com", frozen_branch)
    local_route = script.index("ip -4 route get 1.1.1.1", frozen_branch)
    legacy_else = script.index("\nelse\n    VPS_DOMAIN=", local_route)
    apt_check = script.index("if ! eval apt-get check")
    assert local_route < legacy_else < old_metadata < apt_check
    assert script.index("stale_omr_sources=", local_route) < apt_check
    assert script.index('[ "$OMR_3K_FROZEN" != "yes" ] && [ -f /etc/apt/sources.list.d/openmptcprouter.list ]') < script.index("Update " + "$" + "{REPO} key")
    assert '[ "$OMR_METRICS" = "yes" ] || [ "$OMR_AI" = "yes" ]' in script



@pytest.mark.real_env
def test_legacy_iperf_removal_checks_installed_and_keeps_apt_errors(tmp_path):
    script = (SERVER / "debian9-x86_64.sh").read_text()
    start = script.index('\tif [ "$ARCH" = "amd64" ]; then\n\t\tfor legacy_iperf_pkg')
    end = script.index('\n\tif [ "$SOURCES" = "yes" ]; then', start)
    snippet = "set -e\nARCH=amd64\n" + script[start:end]
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    dpkg = fakebin / "dpkg-query"
    dpkg.write_text(
        '#!/bin/sh\n'
        'case "$*" in\n'
        '  *omr-iperf3*) [ "$INSTALLED_IPERF" = 1 ] && printf "install ok installed" ;;\n'
        '  *omr-libiperf0*) [ "$INSTALLED_LIB" = 1 ] && printf "install ok installed" ;;\n'
        'esac\n'
    )
    apt = fakebin / "apt-get"
    apt.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$APT_TRACE"\nexit "$APT_EXIT"\n')
    dpkg.chmod(0o755)
    apt.chmod(0o755)
    trace = tmp_path / "apt.trace"
    base_env = dict(os.environ, PATH=str(fakebin) + os.pathsep + os.environ["PATH"],
                    APT_TRACE=str(trace), APT_EXIT="0")

    def run(installed_iperf, installed_lib, apt_exit=0):
        trace.write_text("")
        env = dict(base_env, INSTALLED_IPERF=str(installed_iperf),
                   INSTALLED_LIB=str(installed_lib), APT_EXIT=str(apt_exit))
        result = subprocess.run(["sh", "-c", snippet], env=env, capture_output=True, text=True)
        return result, trace.read_text().splitlines()

    result, commands = run(0, 0)
    assert result.returncode == 0 and commands == []
    result, commands = run(1, 0)
    assert result.returncode == 0 and commands == ["-y remove omr-iperf3"]
    result, commands = run(1, 0, apt_exit=42)
    assert result.returncode == 42 and commands == ["-y remove omr-iperf3"]
