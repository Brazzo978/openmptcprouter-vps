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


def test_transport_schema_rejects_ambiguous_combinations(profile_manager,user_client):
    _,runtime=profile_manager
    valid_mptcp=copy.deepcopy(REQ['mptcp'])
    invalid=[
        {'transport':'glorytun_tcp','proxy':'none','mptcp':valid_mptcp,'mqvpn':REQ['mqvpn']},
        {'transport':'mqvpn','proxy':'none','mptcp':valid_mptcp},
        {'transport':'glorytun_tcp','mptcp':valid_mptcp},
        {'proxy':'none','mptcp':valid_mptcp,'mqvpn':REQ['mqvpn']},
        {'transport':'openvpn','proxy':'none','mptcp':valid_mptcp},
    ]
    for payload in invalid:
        assert user_client.post('/profiles/apply',json={'transaction':TX,**payload}).status_code==422
    assert runtime.applies==0


def test_legacy_selection_mutations_are_blocked_while_transaction_pending(profile_manager,user_client):
    mgr,_=profile_manager;mgr.apply(TX,REQ)
    assert user_client.post('/vpn',json={'vpn':'glorytun_tcp'}).status_code==409
    assert user_client.post('/proxy',json={'proxy':'none'}).status_code==409
    assert user_client.post('/vpnips',json={'remoteip':'10.255.255.2','localip':'10.255.255.1'}).status_code==409


def test_capability_version_negotiation_keeps_legacy_response(profile_manager,user_client):
    legacy=user_client.get('/profiles/capabilities').json()
    modern=user_client.get('/profiles/capabilities',params={'version':2}).json()
    assert legacy['version']==1 and modern['version']==2
    assert set(legacy['current'])=={'mptcp','mqvpn'}
    assert user_client.get('/profiles/capabilities',params={'version':3}).status_code==422


def test_v2_route_is_required_before_confirm_and_is_idempotent(profile_manager,user_client):
    mgr,runtime=profile_manager
    runtime.apply=lambda target:None
    runtime.expected_remote=lambda transport:'10.255.255.2'
    applied=[]
    runtime.apply_route=lambda transport,ip:applied.append((transport,ip))
    payload={'transaction':TX,'transport':'glorytun_tcp','proxy':'none','mptcp':REQ['mptcp']}
    assert user_client.post('/profiles/apply',json=payload).status_code==200
    assert user_client.post('/profiles/confirm',json={'transaction':TX}).status_code==409
    wrong={'transaction':TX,'vpnremoteip':'10.255.220.2'}
    assert user_client.post('/profiles/route',json=wrong).status_code==409
    route={'transaction':TX,'vpnremoteip':'10.255.255.2'}
    assert user_client.post('/profiles/route',json=route).json()['route_ready'] is True
    assert user_client.post('/profiles/route',json=route).json()['route_ready'] is True
    assert len(applied)==1
    assert user_client.get('/profiles/status',params={'transaction':TX}).json()['route_ready'] is True
    assert user_client.post('/profiles/confirm',json={'transaction':TX}).json()['state']=='confirmed'


def test_profile_route_requires_authentication(profile_manager,unauth_client):
    route={'transaction':TX,'vpnremoteip':'10.255.255.2'}
    assert unauth_client.post('/profiles/route',json=route).status_code in (401,403)
