"""The remote WireGuard LAN gate is global and defaults to deny."""

import subprocess
from unittest.mock import patch

import pytest

from conftest import app, omr_admin


URL = '/wireguard/remote-access'
HELPER = '/usr/local/sbin/wg-remote-lan-route'


def helper_result(stdout='', returncode=0):
    return subprocess.CompletedProcess([], returncode, stdout, '')


def test_read_requires_auth(unauth_client):
    assert unauth_client.get(URL).status_code == 403


def test_write_requires_auth(unauth_client):
    assert unauth_client.post(URL, json={'lan_access': True}).status_code == 403


def test_default_deny_is_readable_by_authenticated_user(ro_client):
    with patch('omr_admin.path.isfile', return_value=True), patch(
        'omr_admin.subprocess.run', return_value=helper_result('deny\n')
    ) as run:
        response = ro_client.get(URL)
    assert response.status_code == 200
    assert response.json() == {'supported': True, 'lan_access': False}
    run.assert_called_once_with([HELPER, '--lan-access', 'status'],
                                capture_output=True, text=True, check=False, timeout=10)


@pytest.mark.parametrize('body', [{'lan_access': 'true'}, {'lan_access': 1},
                                  {'lan_access': False, 'command': 'allow'}, {}])
def test_rejects_unsafe_body(user_client, body):
    with patch('omr_admin.subprocess.run') as run:
        response = user_client.post(URL, json=body)
    assert response.status_code == 422
    run.assert_not_called()


@pytest.mark.parametrize('client_name', ['ro_client', 'secondary_client'])
def test_readonly_or_secondary_cannot_change_gate(request, client_name):
    client = request.getfixturevalue(client_name)
    with patch('omr_admin.subprocess.run') as run:
        response = client.post(URL, json={'lan_access': True})
    assert response.status_code == 403
    run.assert_not_called()


@pytest.fixture
def secondary_client():
    from conftest import _ASGITestClient
    app.dependency_overrides[omr_admin.get_current_user] = lambda: omr_admin.User(
        username='secondary', userid=2, permissions='rw')
    yield _ASGITestClient(app)
    app.dependency_overrides.pop(omr_admin.get_current_user, None)


@pytest.mark.parametrize('enabled, action, state', [(True, 'allow', 'allow'),
                                                    (False, 'deny', 'deny')])
def test_primary_rw_can_set_and_read_back(user_client, enabled, action, state):
    with patch('omr_admin.path.isfile', return_value=True), patch(
        'omr_admin.subprocess.run', side_effect=[helper_result(), helper_result(state + '\n')]
    ) as run:
        response = user_client.post(URL, json={'lan_access': enabled})
    assert response.status_code == 200
    assert response.json() == {'supported': True, 'lan_access': enabled}
    assert [call.args[0] for call in run.call_args_list] == [
        [HELPER, '--lan-access', action], [HELPER, '--lan-access', 'status']]


def test_admin_can_set_gate(admin_client):
    with patch('omr_admin.path.isfile', return_value=True), patch(
        'omr_admin.subprocess.run', side_effect=[helper_result(), helper_result('allow\n')]
    ):
        response = admin_client.post(URL, json={'lan_access': True})
    assert response.status_code == 200


@pytest.mark.parametrize('method', ['get', 'post'])
def test_missing_helper_is_unavailable(user_client, method):
    with patch('omr_admin.path.isfile', return_value=False), patch(
        'omr_admin.subprocess.run') as run:
        response = getattr(user_client, method)(URL, **({'json': {'lan_access': True}} if method == 'post' else {}))
    assert response.status_code == 503
    run.assert_not_called()


def test_failed_apply_never_claims_success(user_client):
    with patch('omr_admin.path.isfile', return_value=True), patch(
        'omr_admin.subprocess.run', return_value=helper_result(returncode=1)
    ) as run:
        response = user_client.post(URL, json={'lan_access': True})
    assert response.status_code == 502
    run.assert_called_once()


@pytest.mark.parametrize('problem', [subprocess.TimeoutExpired('helper', 10),
                                     OSError('missing')])
def test_helper_execution_error_returns_unavailable(user_client, problem):
    with patch('omr_admin.path.isfile', return_value=True), patch(
        'omr_admin.subprocess.run', side_effect=problem
    ):
        response = user_client.get(URL)
    assert response.status_code == 503


def test_invalid_status_never_claims_success(user_client):
    with patch('omr_admin.path.isfile', return_value=True), patch(
        'omr_admin.subprocess.run', return_value=helper_result('unexpected\n')
    ):
        response = user_client.get(URL)
    assert response.status_code == 502


def test_state_mismatch_reports_failure(user_client):
    with patch('omr_admin.path.isfile', return_value=True), patch(
        'omr_admin.subprocess.run', side_effect=[helper_result(), helper_result('deny\n')]
    ):
        response = user_client.post(URL, json={'lan_access': True})
    assert response.status_code == 502