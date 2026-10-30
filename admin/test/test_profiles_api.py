"""FastAPI auth and transaction integration with synthetic service state."""
import copy
from pathlib import Path

import pytest
from conftest import omr_admin
from test_profiles_transactions import FakeRuntime, REQ, TX
import omr_profiles

pytestmark = pytest.mark.real_env


@pytest.fixture
def profile_manager(tmp_path, monkeypatch):
    runtime = FakeRuntime()
    mgr = omr_profiles.ProfileManager(runtime, tmp_path/'journal.json', tmp_path/'lock',
                                      clock=lambda:1000, enable_timer=False,
                                      monotonic=lambda:1000, boot_id=lambda:'fixture-boot')
    monkeypatch.setattr(omr_admin, '_profile_manager', mgr)
    return mgr, runtime


def test_authentication_and_primary_write_permission(profile_manager, unauth_client, ro_client):
    assert unauth_client.get('/profiles/capabilities').status_code in (401,403)
    assert ro_client.get('/profiles/capabilities').status_code == 403
    assert ro_client.post('/profiles/apply', json={'transaction':TX, **REQ}).status_code == 403


def test_roundtrip_and_idempotent_confirm(profile_manager, user_client):
    mgr, runtime = profile_manager
    response = user_client.get('/profiles/capabilities')
    assert response.status_code == 200
    assert response.json()['supported'] is True
    assert 'fixture-secret-key' not in response.text
    applied = user_client.post('/profiles/apply', json={'transaction':TX, **REQ})
    assert applied.status_code == 200
    assert applied.json()['state'] == 'pending'
    assert applied.json()['seconds_remaining'] == 240
    status = user_client.get('/profiles/status', params={'transaction': TX})
    assert status.json()['state'] == 'pending'
    for _ in range(2):
        result = user_client.post('/profiles/confirm', json={'transaction':TX})
        assert result.status_code == 200
        assert result.json()['state'] == 'confirmed'
    assert runtime.applies == 1
    assert mgr.status(TX)['state'] == 'confirmed'


def test_validation_rejects_credential_and_unknown_fields_before_mutation(profile_manager, user_client):
    _, runtime = profile_manager
    for location in ('top', 'mptcp', 'mqvpn', 'reorder'):
        payload = {'transaction':TX, **copy.deepcopy(REQ)}
        if location == 'top': payload['users'] = [{'key':'fixture-key'}]
        elif location == 'reorder': payload['mqvpn']['reorder'] = {'enabled':'on', 'auth_key':'fixture-key'}
        else: payload[location]['auth_key'] = 'fixture-key'
        assert user_client.post('/profiles/apply', json=payload).status_code == 422
    assert runtime.applies == 0


def test_nanbbr_range_and_strict_bool(profile_manager, user_client):
    _, runtime = profile_manager
    invalid = []
    for value in (0, 101, True):
        payload={'transaction':TX, **copy.deepcopy(REQ)}
        payload['mptcp']['nanbbr_aggressiveness'] = value
        invalid.append(payload)
    for value in ('false', 0, 1):
        payload={'transaction':TX, **copy.deepcopy(REQ)}
        payload['mqvpn']['fec_enable'] = value
        invalid.append(payload)
    payload={'transaction':TX, **copy.deepcopy(REQ)}
    payload['mqvpn']['reorder']={'cap_packets':3}
    invalid.append(payload)
    for payload in invalid:
        assert user_client.post('/profiles/apply', json=payload).status_code == 422
    assert runtime.applies == 0


def test_legacy_mptcp_and_mqvpn_mutations_rejected_while_pending(profile_manager, user_client):
    mgr, _ = profile_manager
    mgr.apply(TX, REQ)
    mptcp = {'checksum':'0', 'path_manager':'kernel', 'scheduler':'default',
             'syn_retries':3, 'congestion_control':'bbr'}
    assert user_client.post('/mptcp', json=mptcp).status_code == 409
    assert user_client.post('/mqvpn', json={'key':'fixture','scheduler':'wlb'}).status_code == 409


def test_manual_rollback_restores_previous_values(profile_manager, user_client):
    mgr, runtime = profile_manager
    before=runtime.current()
    assert user_client.post('/profiles/apply', json={'transaction':TX, **REQ}).status_code == 200
    response=user_client.post('/profiles/rollback', json={'transaction':TX})
    assert response.status_code == 200
    assert response.json()['state']=='rolled_back'
    assert runtime.current()==before
    assert mgr.status(TX)['state']=='rolled_back'
