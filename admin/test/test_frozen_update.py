"""The reviewed 3K VPS source freeze must reject in-place API updates."""
from fastapi import HTTPException
import pytest
from conftest import RW_USER, omr_admin


def test_update_rejected_before_side_effects(monkeypatch):
    monkeypatch.setattr(
        omr_admin.path, "isfile",
        lambda filename: filename == "/etc/omr-vps-3k-frozen.json",
    )
    def forbidden(*args, **kwargs):
        raise AssertionError("frozen update reached a side effect")
    monkeypatch.setattr(omr_admin.subprocess, "run", forbidden)
    monkeypatch.setattr(omr_admin, "open", forbidden, raising=False)
    with pytest.raises(HTTPException) as error:
        omr_admin.update(current_user=RW_USER)
    assert error.value.status_code == 409
    assert "frozen 3K" in error.value.detail
