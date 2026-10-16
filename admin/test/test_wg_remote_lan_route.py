"""Offline behavior of the road-warrior LAN route timer helper."""

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.real_env
HELPER = Path(__file__).resolve().parents[2] / "wg-remote-lan-route"


def load_helper(tmp_path):
    loader = importlib.machinery.SourceFileLoader("wg_remote_lan_route_test", str(HELPER))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    module.STATE = tmp_path / "wg-remote-lan-access.enabled"
    module.LOCK = tmp_path / "wg-remote-lan-access.lock"
    module.NFT_RULESET = tmp_path / "omr.nft"
    module.NFT_RULESET.write_text("test fixture")
    module.MQVPN_CONFIG = tmp_path / "mqvpn-server.json"
    module._real_sync_nft = module.sync_nft
    module.sync_nft = lambda *args: None
    return module


def write_config(tmp_path, router):
    config = tmp_path / "omr-admin-config.json"
    config.write_text(json.dumps({"users": [{"openmptcprouter": router}]}))
    return config


def argv(monkeypatch, config, *options):
    monkeypatch.setattr(sys, "argv", ["wg-remote-lan-route", "--config", str(config), *options])


def connected_client_interface(monkeypatch, helper):
    real_path = Path

    class ClientInterface:
        def exists(self):
            return True

    def path(value):
        if str(value) == "/sys/class/net/client-wg0":
            return ClientInterface()
        return real_path(value)

    monkeypatch.setattr(helper, "Path", path)


@pytest.mark.parametrize("router", [{}, {"vpnremoteip": ""}, {"vpnremoteip": "  "}])
def test_fresh_config_waits_without_route_lookup(tmp_path, monkeypatch, capsys, router):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, router)
    assert helper.configured_lan(config) == (None, [])
    argv(monkeypatch, config, "--dry-run")
    monkeypatch.setattr(helper, "output", lambda *args: pytest.fail("unexpected ip lookup"))

    assert helper.main() == 0
    assert capsys.readouterr().out == ""


def test_mqvpn_lan_dry_run_uses_private_table_only(tmp_path, monkeypatch, capsys):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, {
        "vpnremoteip": "10.255.220.2", "lanips": ["192.168.100.42/24"]
    })
    argv(monkeypatch, config, "--dry-run", "--tunnel-dev", "mqvpn0", "--lan-access", "allow")
    monkeypatch.setattr(helper, "output", lambda *args: pytest.fail("unexpected ip lookup"))

    assert helper.main() == 0
    assert capsys.readouterr().out.splitlines() == [
        "ip -4 route replace 192.168.100.0/24 via 10.255.220.2 dev mqvpn0 onlink table 24612",
        "ip -4 rule add pref 12460 iif client-wg0 lookup 24612",
    ]


@pytest.mark.parametrize("router", [
    {"vpnremoteip": "not-an-ip", "lanips": ["192.168.100.0/24"]},
    {"vpnremoteip": "8.8.8.8", "lanips": ["192.168.100.0/24"]},
    {"vpnremoteip": "10.255.220.2", "lanips": ["bad-network"]},
    {"lanips": ["bad-network"]},
])
def test_invalid_explicit_config_still_fails(tmp_path, router):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, router)
    with pytest.raises(ValueError):
        helper.configured_lan(config)


def test_missing_router_address_cleans_stale_private_policy(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, {"lanips": ["192.168.100.0/24"]})
    argv(monkeypatch, config)
    connected_client_interface(monkeypatch, helper)
    commands = []
    monkeypatch.setattr(helper, "current_routes", lambda: {"192.168.50.0/24"})
    monkeypatch.setattr(helper, "rule_present", lambda: True)
    monkeypatch.setattr(helper, "apply", lambda command, dry_run: commands.append((command, dry_run)))
    monkeypatch.setattr(helper, "output", lambda *args: pytest.fail("unexpected route lookup"))

    assert helper.main() == 0
    assert commands == [
        (["ip", "-4", "route", "del", "192.168.50.0/24", "table", "24612"], False),
        (["ip", "-4", "rule", "del", "pref", "12460", "iif", "client-wg0",
          "lookup", "24612"], False),
    ]


def test_main_interface_route_waits_and_cleans_stale_policy(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, {
        "vpnremoteip": "10.255.220.2", "lanips": ["192.168.100.0/24"]
    })
    argv(monkeypatch, config)
    connected_client_interface(monkeypatch, helper)
    commands = []
    monkeypatch.setattr(helper, "output", lambda *args: json.dumps([{"dev": "eth0"}]))
    monkeypatch.setattr(helper, "current_routes", lambda: {"192.168.50.0/24"})
    monkeypatch.setattr(helper, "rule_present", lambda: True)
    monkeypatch.setattr(helper, "apply", lambda command, dry_run: commands.append((command, dry_run)))

    assert helper.main() == 0
    assert commands == [
        (["ip", "-4", "route", "del", "192.168.50.0/24", "table", "24612"], False),
        (["ip", "-4", "rule", "del", "pref", "12460", "iif", "client-wg0",
          "lookup", "24612"], False),
    ]


def test_ip_lookup_failure_is_not_treated_as_missing_tunnel(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, {
        "vpnremoteip": "10.255.220.2", "lanips": ["192.168.100.0/24"]
    })
    argv(monkeypatch, config, "--lan-access", "allow")
    connected_client_interface(monkeypatch, helper)

    def failed_lookup(*args):
        raise subprocess.CalledProcessError(2, args)

    monkeypatch.setattr(helper, "output", failed_lookup)
    with pytest.raises(subprocess.CalledProcessError):
        helper.main()


def test_absent_policy_table_is_normal_on_fresh_config(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, {})
    argv(monkeypatch, config)
    connected_client_interface(monkeypatch, helper)
    calls = []

    def ip_output(*command):
        calls.append(command)
        if command == ("ip", "-j", "-N", "-4", "route", "show", "table", "all"):
            return json.dumps([{"dst": "default", "table": "254", "dev": "eth0"}])
        if command == ("ip", "-4", "rule", "show"):
            return "0: from all lookup local\n32766: from all lookup main\n"
        pytest.fail(f"unexpected ip command: {command}")

    monkeypatch.setattr(helper, "output", ip_output)
    monkeypatch.setattr(helper, "apply", lambda *args: pytest.fail("unexpected route change"))

    assert helper.main() == 0
    assert calls == [
        ("ip", "-j", "-N", "-4", "route", "show", "table", "all"),
        ("ip", "-4", "rule", "show"),
    ]


def test_route_listing_selects_only_numeric_private_table(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)
    routes = [
        {"dst": "default", "dev": "eth0"},
        {"dst": "192.168.1.0/24", "table": "254"},
        {"dst": "192.168.50.0/24", "table": "24612"},
        {"dst": "192.168.60.0/24", "table": 24612},
    ]
    monkeypatch.setattr(helper, "output", lambda *args: json.dumps(routes))

    assert helper.current_routes() == {"192.168.50.0/24", "192.168.60.0/24"}


def test_private_table_query_failure_is_not_hidden(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)

    def failed_query(*args):
        raise subprocess.CalledProcessError(2, args)

    monkeypatch.setattr(helper, "output", failed_query)
    with pytest.raises(subprocess.CalledProcessError):
        helper.current_routes()
    with pytest.raises(subprocess.CalledProcessError):
        helper.rule_present()


def test_route_update_failure_still_fails_timer(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, {
        "vpnremoteip": "10.255.220.2", "lanips": ["192.168.100.0/24"]
    })
    argv(monkeypatch, config, "--lan-access", "allow")
    connected_client_interface(monkeypatch, helper)
    monkeypatch.setattr(helper, "output", lambda *args: json.dumps([{"dev": "tun0"}]))
    monkeypatch.setattr(helper, "current_routes", lambda: set())

    def failed_update(command, dry_run):
        raise subprocess.CalledProcessError(2, command)

    monkeypatch.setattr(helper, "apply", failed_update)
    with pytest.raises(subprocess.CalledProcessError):
        helper.main()


def test_gate_defaults_deny_and_status_is_read_only(tmp_path, monkeypatch, capsys):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, {})
    argv(monkeypatch, config, "--lan-access", "status")
    monkeypatch.setattr(helper, "output", lambda *args: pytest.fail("unexpected ip lookup"))
    assert helper.main() == 0
    assert capsys.readouterr().out == "deny\n"
    assert not helper.STATE.exists()
    assert not helper.LOCK.exists()


def test_gate_persists_root_only_and_revoke_clears_stale_policy(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, {
        "vpnremoteip": "10.255.239.2", "lanips": ["192.168.239.2/24"]
    })
    connected_client_interface(monkeypatch, helper)
    calls = []
    monkeypatch.setattr(helper, "sync_nft",
                        lambda remote, nets: calls.append(("nft", str(remote), [str(n) for n in nets])))
    monkeypatch.setattr(helper, "output",
                        lambda *args: json.dumps([{"dev": "tun3kqa"}]))
    monkeypatch.setattr(helper, "current_routes", lambda: {"192.168.239.0/24"})
    monkeypatch.setattr(helper, "rule_present", lambda: True)
    monkeypatch.setattr(helper, "apply",
                        lambda command, dry_run: calls.append(("ip", command, dry_run)))

    argv(monkeypatch, config, "--lan-access", "allow")
    assert helper.main() == 0
    assert helper.STATE.read_text() == "allow\n"
    assert helper.STATE.stat().st_mode & 0o777 == 0o600
    assert calls[-1] == ("nft", "10.255.239.2", ["192.168.239.0/24"])
    assert any("route" in call[1] and "replace" in call[1] for call in calls[:-1])

    calls.clear()
    argv(monkeypatch, config, "--lan-access", "deny")
    assert helper.main() == 0
    assert not helper.STATE.exists()
    assert calls[0] == ("nft", "10.255.239.2", [])
    assert [call[1][3] for call in calls[1:]] == ["del", "del"]


def test_nft_sets_change_in_one_transaction(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)
    commands = []

    def nft_run(command, **kwargs):
        commands.append((command, kwargs))
    monkeypatch.setattr(helper.subprocess, "run", nft_run)
    remote = helper.ipaddress.IPv4Address("10.255.239.2")
    nets = [helper.ipaddress.IPv4Network("192.168.239.0/25"),
            helper.ipaddress.IPv4Network("192.168.239.128/25")]
    helper._real_sync_nft(remote, nets)
    assert len(commands) == 1
    assert commands[0][0] == ["nft", "-f", "-"]
    assert commands[0][1]["check"] is True
    assert commands[0][1]["input"].splitlines() == [
        "flush set inet omr wg_remote_gui_v4",
        "flush set inet omr wg_remote_lan_v4",
        "add element inet omr wg_remote_gui_v4 { 10.255.239.2 }",
        "add element inet omr wg_remote_lan_v4 { 192.168.239.0/24 }",
    ]


def test_default_deny_keeps_gui_set_without_lan_or_route_lookup(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, {
        "vpnremoteip": "10.255.239.2", "lanips": ["192.168.239.0/24"]
    })
    argv(monkeypatch, config)
    connected_client_interface(monkeypatch, helper)
    calls = []
    monkeypatch.setattr(helper, "sync_nft",
                        lambda remote, nets: calls.append(("nft", str(remote), list(nets))))
    monkeypatch.setattr(helper, "current_routes", lambda: set())
    monkeypatch.setattr(helper, "rule_present", lambda: False)

    def ip_output(*command):
        if command == ("ip", "-4", "rule", "show"):
            return ""
        pytest.fail(f"unexpected route lookup: {command}")

    monkeypatch.setattr(helper, "output", ip_output)
    assert helper.main() == 0
    assert calls == [("nft", "10.255.239.2", [])]


def test_enabled_gate_waits_for_tunnel_with_lan_set_empty(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, {
        "vpnremoteip": "10.255.239.2", "lanips": ["192.168.239.0/24"]
    })
    argv(monkeypatch, config)
    connected_client_interface(monkeypatch, helper)
    helper.set_lan_access(True)
    calls = []
    monkeypatch.setattr(helper, "sync_nft",
                        lambda remote, nets: calls.append((str(remote), list(nets))))
    monkeypatch.setattr(helper, "output",
                        lambda *args: json.dumps([{"dev": "eth0"}]))
    monkeypatch.setattr(helper, "current_routes", lambda: set())
    monkeypatch.setattr(helper, "rule_present", lambda: False)
    assert helper.main() == 0
    assert calls == [("10.255.239.2", [])]


def test_explicit_invalid_router_address_fails_without_opening_gate(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, {
        "vpnremoteip": "not-an-ip", "lanips": ["192.168.239.0/24"]
    })
    argv(monkeypatch, config, "--lan-access", "allow")
    calls = []
    monkeypatch.setattr(helper, "sync_nft",
                        lambda remote, nets: calls.append((remote, nets)))
    monkeypatch.setattr(helper, "current_routes", lambda: set())
    monkeypatch.setattr(helper, "rule_present", lambda: False)
    with pytest.raises(ValueError):
        helper.main()
    assert calls and all(call == (None, []) for call in calls)
    assert not helper.STATE.exists()  # failed validation must not claim allow

def test_firewall_checks_both_client_directions_before_conntrack():
    ruleset = (HELPER.parent / "nftables" / "omr.nft").read_text()
    forward = ruleset.split("\tchain forward {", 1)[1].split("\tchain output {", 1)[0]
    established = forward.index("ct state established,related accept")
    assert forward.index("jump wg_remote_access") < established
    assert forward.index("jump wg_remote_return") < established
    assert "ip daddr @wg_remote_nonpublic_v4 reject" in ruleset
    assert "ip saddr @wg_remote_nonpublic_v4 reject" in ruleset

def test_failed_allow_revokes_state_and_keeps_lan_set_closed(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, {
        "vpnremoteip": "10.255.220.2", "lanips": ["192.168.100.0/24"]
    })
    argv(monkeypatch, config, "--lan-access", "allow")
    connected_client_interface(monkeypatch, helper)
    monkeypatch.setattr(helper, "output", lambda *args: json.dumps([{"dev": "tun0"}]))
    calls = []
    monkeypatch.setattr(helper, "sync_nft", lambda remote, nets: calls.append(list(nets)))
    monkeypatch.setattr(helper, "current_routes", lambda: set())
    monkeypatch.setattr(helper, "rule_present", lambda: False)
    def failing_apply(command, dry_run):
        raise subprocess.CalledProcessError(2, command)
    monkeypatch.setattr(helper, "apply", failing_apply)
    with pytest.raises(subprocess.CalledProcessError):
        helper.main()
    assert calls and all(not networks for networks in calls)
    assert not helper.STATE.exists()


def test_timer_refresh_does_not_temporarily_close_lan_set(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, {
        "vpnremoteip": "10.255.220.2", "lanips": ["192.168.100.0/24"]
    })
    helper.set_lan_access(True)
    argv(monkeypatch, config)
    connected_client_interface(monkeypatch, helper)
    monkeypatch.setattr(helper, "output", lambda *args: json.dumps([{"dev": "tun0"}]))
    monkeypatch.setattr(helper, "current_routes", lambda: {"192.168.100.0/24"})
    monkeypatch.setattr(helper, "rule_present", lambda: True)
    monkeypatch.setattr(helper, "apply", lambda *args: None)
    calls = []
    monkeypatch.setattr(helper, "sync_nft", lambda remote, nets: calls.append(list(nets)))
    assert helper.main() == 0
    assert calls == [[helper.ipaddress.IPv4Network("192.168.100.0/24")]]
    assert helper.STATE.read_text() == "allow\n"


def test_mqvpn_gate_registers_and_verifies_routes_before_firewall(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, {
        "userid": 0, "vpnremoteip": "10.255.220.2",
        "lanips": ["192.168.100.42/24"]
    })
    helper.MQVPN_CONFIG = tmp_path / "mqvpn-server.json"
    helper.MQVPN_CONFIG.write_text('{"control_listen":"127.0.0.1:9090"}')
    argv(monkeypatch, config, "--lan-access", "allow")
    connected_client_interface(monkeypatch, helper)
    monkeypatch.setattr(helper, "output", lambda *args: json.dumps([{"dev": "mqvpn0"}]))
    monkeypatch.setattr(helper, "current_routes", lambda: set())
    monkeypatch.setattr(helper, "rule_present", lambda: False)
    calls = []
    def control(command):
        calls.append(("control", command))
        if command["cmd"] == "replace_client_routes":
            return {"ok": True, "n_routes": 1}
        return {"ok": True, "user": "openmptcprouter",
                "routes": ["192.168.100.0/24"], "session_count": 1}
    monkeypatch.setattr(helper, "mqvpn_control", control)
    monkeypatch.setattr(helper, "apply", lambda command, dry: calls.append(("ip", command)))
    monkeypatch.setattr(helper, "sync_nft", lambda remote, nets: calls.append(("nft", list(nets))))
    assert helper.main() == 0
    assert [call[0] for call in calls[:2]] == ["control", "control"]
    assert calls[-1] == ("nft", [helper.ipaddress.IPv4Network("192.168.100.0/24")])
    assert helper.STATE.read_text() == "allow\n"


def test_mqvpn_missing_session_closes_gate_without_revoking_native_routes(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, {
        "userid": 0, "vpnremoteip": "10.255.220.2",
        "lanips": ["192.168.100.0/24"]
    })
    helper.MQVPN_CONFIG = tmp_path / "mqvpn-server.json"
    helper.MQVPN_CONFIG.write_text('{}')
    argv(monkeypatch, config, "--lan-access", "allow")
    connected_client_interface(monkeypatch, helper)
    monkeypatch.setattr(helper, "output", lambda *args: json.dumps([{"dev": "mqvpn0"}]))
    monkeypatch.setattr(helper, "current_routes", lambda: set())
    monkeypatch.setattr(helper, "rule_present", lambda: False)
    control_commands = []
    def control(command):
        control_commands.append(command)
        if command["cmd"] == "replace_client_routes":
            return {"ok": True, "n_routes": 1}
        return {"ok": True, "user": "openmptcprouter",
                "routes": ["192.168.100.0/24"], "session_count": 0}
    monkeypatch.setattr(helper, "mqvpn_control", control)
    lan_sets = []
    monkeypatch.setattr(helper, "sync_nft", lambda remote, nets: lan_sets.append(list(nets)))
    with pytest.raises(ValueError, match="not ready"):
        helper.main()
    assert lan_sets and all(not nets for nets in lan_sets)
    assert not helper.STATE.exists()
    assert not any(cmd.get("routes") == [] for cmd in control_commands)


def test_gate_deny_retains_native_mqvpn_routes(tmp_path, monkeypatch):
    helper = load_helper(tmp_path)
    config = write_config(tmp_path, {
        "userid": 0, "vpnremoteip": "10.255.220.2",
        "lanips": ["192.168.100.0/24"]
    })
    helper.MQVPN_CONFIG = tmp_path / "mqvpn-server.json"
    helper.MQVPN_CONFIG.write_text('{}')
    argv(monkeypatch, config, "--lan-access", "deny")
    commands = []
    monkeypatch.setattr(helper, "current_routes", lambda: set())
    monkeypatch.setattr(helper, "rule_present", lambda: False)
    monkeypatch.setattr(helper, "sync_nft", lambda remote, nets: commands.append(("nft", list(nets))))
    monkeypatch.setattr(helper, "mqvpn_control", lambda command: commands.append(("control", command)) or
                        {"ok": True, "n_routes": 1})
    assert helper.main() == 0
    assert commands[0] == ("nft", [])
    assert commands[1][1]["routes"] == ["192.168.100.0/24"]
    assert not helper.STATE.exists()
