"""NanBBR VPS contract and rollback with every mutable path in tmp_path."""
import builtins
import io
import json
import os
import subprocess
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from conftest import RW_USER, omr_admin


PAYLOAD = {
    "checksum": "0",
    "path_manager": "kernel",
    "scheduler": "default",
    "syn_retries": 3,
    "congestion_control": "nanbbr1_var",
    "version": 1,
    "nanbbr_aggressiveness": 80,
}


@pytest.mark.parametrize("value", [0, 101])
def test_aggressiveness_range(value):
    with pytest.raises(ValidationError):
        omr_admin.MPTCPparams(**{**PAYLOAD, "nanbbr_aggressiveness": value})


def test_var_requires_aggressiveness():
    params = omr_admin.MPTCPparams(**{k: v for k, v in PAYLOAD.items()
                                      if k != "nanbbr_aggressiveness"})
    assert omr_admin.mptcp(params=params, current_user=RW_USER)["result"] == "error"


@pytest.mark.real_env
@pytest.mark.parametrize("fail_cc", [False, True])
def test_var_apply_and_rollback(tmp_path, monkeypatch, fail_cc):
    sysctl_file = tmp_path / "90-shadowsocks.conf"
    sysctl_file.write_text("net.core.somaxconn=4096\n")
    config_file = tmp_path / "nanbbr-var.json"
    parameter_file = tmp_path / "nanbbr1_var"
    parameter_file.write_text("50\n")
    monkeypatch.setattr(omr_admin, "MPTCP_LOCK_FILE", str(tmp_path / "mptcp.lock"))
    monkeypatch.setattr(omr_admin, "MPTCP_SYSCTL_FILE", str(sysctl_file))
    monkeypatch.setattr(omr_admin, "NANBBR_CONFIG_FILE", str(config_file))
    monkeypatch.setattr(
        omr_admin, "nanbbr_parameter_path",
        lambda cc: str(parameter_file if cc == "nanbbr1_var" else tmp_path / cc),
    )
    real_exists = os.path.exists
    monkeypatch.setattr(
        omr_admin.path, "exists",
        lambda p: False if str(p).startswith("/proc/sys/net/mptcp/")
        else real_exists(p),
    )
    real_open = builtins.open
    def fake_open(filename, mode="r", *args, **kwargs):
        if str(filename) == "/proc/sys/net/ipv4/tcp_available_congestion_control":
            return io.StringIO("reno bbr nanbbr1_var\n")
        return real_open(filename, mode, *args, **kwargs)
    monkeypatch.setattr(builtins, "open", fake_open)
    state = {
        "net.mptcp.checksum_enabled": "0",
        "net.ipv4.tcp_congestion_control": "bbr",
    }
    def fake_run(command, **kwargs):
        if command[0] == "modprobe":
            return SimpleNamespace(returncode=0, stdout="")
        if command[:2] == ["sysctl", "-n"]:
            return SimpleNamespace(returncode=0, stdout=state[command[2]] + "\n")
        if command[:2] == ["sysctl", "-qw"]:
            key, value = command[2].split("=", 1)
            if fail_cc and key == "net.ipv4.tcp_congestion_control" and value == "nanbbr1_var":
                raise subprocess.CalledProcessError(1, command)
            state[key] = value
            return SimpleNamespace(returncode=0, stdout="")
        raise AssertionError(command)
    monkeypatch.setattr(omr_admin.subprocess, "run", fake_run)
    monkeypatch.setattr(omr_admin.os, "system", lambda command: 0)
    result = omr_admin.mptcp(
        params=omr_admin.MPTCPparams(**PAYLOAD), current_user=RW_USER)
    if fail_cc:
        assert result["result"] == "error"
        assert parameter_file.read_text().strip() == "50"
        assert state["net.ipv4.tcp_congestion_control"] == "bbr"
        assert sysctl_file.read_text() == "net.core.somaxconn=4096\n"
        assert not config_file.exists()
    else:
        assert result["result"] == "done"
        assert parameter_file.read_text().strip() == "80"
        assert state["net.ipv4.tcp_congestion_control"] == "nanbbr1_var"
        assert json.loads(config_file.read_text())["aggressiveness"] == 80
        assert "net.ipv4.tcp_congestion_control=nanbbr1_var" in sysctl_file.read_text()


@pytest.mark.real_env
def test_missing_var_module_is_rejected_before_sysctl(tmp_path, monkeypatch):
    monkeypatch.setattr(omr_admin, "MPTCP_LOCK_FILE", str(tmp_path / "mptcp.lock"))
    monkeypatch.setattr(
        omr_admin, "nanbbr_parameter_path",
        lambda cc: str(tmp_path / cc),
    )
    monkeypatch.setattr(
        omr_admin.subprocess, "run",
        lambda cmd, **kw: SimpleNamespace(returncode=1, stdout=""),
    )
    result = omr_admin.mptcp(
        params=omr_admin.MPTCPparams(**PAYLOAD), current_user=RW_USER)
    assert result["result"] == "error"
    assert "not supported" in result["reason"]


@pytest.mark.real_env
def test_capability_requires_writable_parameter(tmp_path, monkeypatch):
    parameter = tmp_path / "nanbbr1_var"
    parameter.write_text("50\n")
    monkeypatch.setattr(
        omr_admin, "nanbbr_parameter_path",
        lambda cc: str(tmp_path / cc),
    )
    real_access = os.access
    monkeypatch.setattr(
        omr_admin.os, "access",
        lambda p, mode: False if str(p) == str(parameter) else real_access(p, mode),
    )
    assert not any(omr_admin.nanbbr_capabilities().values())
    monkeypatch.setattr(omr_admin.os, "access", real_access)
    capabilities = omr_admin.nanbbr_capabilities()
    assert capabilities == {
        "nanbbr1_var": True, "nanbbr2_var": False, "nanbbr3_var": False,
    }


@pytest.mark.real_env
@pytest.mark.parametrize("value, expected", [(25, 25), (101, None), ("bad", None)])
def test_persisted_aggressiveness_bounds(tmp_path, monkeypatch, value, expected):
    config = tmp_path / "nanbbr-var.json"
    config.write_text(json.dumps({"aggressiveness": value}))
    monkeypatch.setattr(omr_admin, "NANBBR_CONFIG_FILE", str(config))
    assert omr_admin.read_nanbbr_aggressiveness() == expected
