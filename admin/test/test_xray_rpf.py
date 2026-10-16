"""Dedicated XRay reverse TCP forwarding: config, user isolation, API scope."""
import copy
import pytest

from conftest import omr_admin

USER_UUID = "11111111-1111-4111-8111-111111111111"
OTHER_UUID = "22222222-2222-4222-8222-222222222222"
PAYLOAD = {"name": "router 18080", "port": "18080", "proto": "tcp",
           "destip": "192.168.1.10", "destport": "8080"}


def test_distinct_public_and_destination_ports_with_tls_reverse():
    data = {"inbounds": [], "routing": {"rules": []}}
    omr_admin._xray_rpf_set(data, "openmptcprouter", 18080, "192.168.1.10", 8080, USER_UUID)
    listener, public = data["inbounds"]
    assert listener["port"] == 65444
    assert listener["settings"]["clients"][0]["id"] == USER_UUID
    assert listener["settings"]["clients"][0]["reverse"] == {
        "tag": "omr-rpf-reverse-openmptcprouter"}
    assert listener["streamSettings"]["security"] == "tls"
    assert listener["streamSettings"]["sockopt"] == {"tcpMptcp": True, "mark": 0}
    assert public["port"] == 18080
    assert public["settings"]["portMap"] == {"18080": "192.168.1.10:8080"}
    assert data["routing"]["rules"] == [{
        "type": "field", "inboundTag": [public["tag"]],
        "outboundTag": "omr-rpf-reverse-openmptcprouter"}]
    assert omr_admin._render_xray_rpf_bypass(data) == [
        'meta nfproto ipv4 tcp dport 18080 accept comment "OMR XRay RPF bypass 18080"']


def test_update_is_idempotent_and_can_change_destination():
    data = {"inbounds": [], "routing": {"rules": []}}
    omr_admin._xray_rpf_set(data, "openmptcprouter", 18080, "192.168.1.10", 8080, USER_UUID)
    original = copy.deepcopy(data)
    omr_admin._xray_rpf_set(data, "openmptcprouter", 18080, "192.168.1.10", 8080, USER_UUID)
    assert data == original
    omr_admin._xray_rpf_set(data, "openmptcprouter", 18080, "192.168.1.11", 9000, USER_UUID)
    assert len(data["inbounds"]) == 2
    assert len(data["routing"]["rules"]) == 1
    assert data["inbounds"][1]["settings"]["portMap"] == {"18080": "192.168.1.11:9000"}


def test_users_have_separate_reverse_tags_and_ports():
    data = {"inbounds": [], "routing": {"rules": []}}
    omr_admin._xray_rpf_set(data, "openmptcprouter", 18080, "192.168.1.10", 8080, USER_UUID)
    with pytest.raises(ValueError, match="already in use"):
        omr_admin._xray_rpf_set(data, "other", 18080, "192.168.2.10", 8080, OTHER_UUID)
    omr_admin._xray_rpf_set(data, "other", 18081, "192.168.2.10", 8080, OTHER_UUID)
    listener = data["inbounds"][0]
    assert {c["email"] for c in listener["settings"]["clients"]} == {
        "openmptcprouter", "other"}
    assert omr_admin._xray_rpf_remove(data, "openmptcprouter", 18080)
    assert {c["email"] for c in listener["settings"]["clients"]} == {"other"}
    assert not omr_admin._xray_rpf_remove(data, "openmptcprouter", 18080)
    assert omr_admin._xray_rpf_remove(data, "other", 18081)
    assert data["inbounds"] == []


@pytest.mark.parametrize("port,proto,ip,destport", [
    ("18080", "udp", "192.168.1.10", "8080"),
    ("18080-18081", "tcp", "192.168.1.10", "8080"),
    ("65000", "tcp", "192.168.1.10", "8080"),
    ("18080", "tcp", "2001:db8::1", "8080"),
    ("18080", "tcp", "192.168.1.10", "65536"),
])
def test_invalid_or_unsupported_rule_is_rejected(port, proto, ip, destport):
    with pytest.raises(ValueError):
        omr_admin._xray_rpf_parameters(port, proto, ip, destport)


def test_endpoints_require_auth(unauth_client):
    assert unauth_client.post("/xrayrpfredirect", json=PAYLOAD).status_code == 403
    assert unauth_client.post("/xrayrpfunredirect", json=PAYLOAD).status_code == 403


def test_read_only_user_cannot_mutate(ro_client):
    assert ro_client.post("/xrayrpfredirect", json=PAYLOAD).json()["result"] == "permission"
    assert ro_client.post("/xrayrpfunredirect", json=PAYLOAD).json()["result"] == "permission"


def test_endpoint_keeps_current_user_scope(user_client, monkeypatch):
    called = []
    monkeypatch.setattr(omr_admin.os.path, "isfile", lambda _: True)
    monkeypatch.setattr(omr_admin, "xray_rpf_add_port",
                        lambda user, *args: called.append((user.username, args)) or
                        {"result": "done"})
    assert user_client.post("/xrayrpfredirect", json=PAYLOAD).json()["result"] == "done"
    assert called == [("openmptcprouter",
                       ("18080", "tcp", "router 18080", "192.168.1.10", "8080"))]


@pytest.mark.real_env
def test_http_crud_writes_only_temporary_config(user_client, tmp_path, monkeypatch):
    """Exercise real route -> config write -> route removal, with all effects fenced."""
    import json
    from unittest.mock import MagicMock
    from conftest import _run_in_threadpool_direct

    config_file = tmp_path / "xray-server.json"
    config_file.write_text(json.dumps({
        "inbounds": [], "routing": {"rules": []},
        "outbounds": [{"tag": "direct", "protocol": "freedom"}],
    }))
    firewall_calls = []
    command_calls = []
    nft_calls = []
    monkeypatch.setattr(omr_admin, "XRAY_RPF_CONFIG", str(config_file))
    monkeypatch.setattr(omr_admin, "read_omr_config", lambda: {
        "users": [{"openmptcprouter": {"xray": {"key": USER_UUID}}}]
    })
    monkeypatch.setattr(omr_admin.subprocess, "run", lambda command, **kw:
                        command_calls.append(command) or MagicMock(returncode=0))
    monkeypatch.setattr(omr_admin, "_nft_sync_xray_rpf",
                        lambda data: nft_calls.append(copy.deepcopy(data)))
    monkeypatch.setattr(omr_admin, "shorewall_add_port",
                        lambda *args, **kw: firewall_calls.append(("add", args, kw)))
    monkeypatch.setattr(omr_admin, "shorewall_del_port",
                        lambda *args, **kw: firewall_calls.append(("del", args, kw)))
    monkeypatch.setattr("fastapi.routing.run_in_threadpool",
                        _run_in_threadpool_direct)

    assert user_client.post("/xrayrpfredirect", json=PAYLOAD).json()["result"] == "done"
    configured = json.loads(config_file.read_text())
    assert configured["inbounds"][1]["settings"]["portMap"] == {
        "18080": "192.168.1.10:8080"
    }
    assert firewall_calls[0][0] == "add"
    assert command_calls[0][:4] == ["/usr/bin/xray", "run", "-test", "-config"]
    assert command_calls[1] == ["systemctl", "-q", "restart", "xray"]
    assert len(nft_calls) == 1

    udp = {**PAYLOAD, "proto": "udp"}
    assert user_client.post("/xrayrpfredirect", json=udp).json()["result"] == "error"
    assert json.loads(config_file.read_text()) == configured

    assert user_client.post("/xrayrpfunredirect", json=PAYLOAD).json()["result"] == "done"
    assert json.loads(config_file.read_text())["inbounds"] == []
    assert firewall_calls[-1][0] == "del"
    assert len(nft_calls) == 2
