"""Authentication and isolation of the new informational dashboard routes."""
from unittest.mock import patch
from types import SimpleNamespace
import asyncio
import pytest
from conftest import omr_admin, make_token


def test_snapshot_requires_authentication(unauth_client):
    with patch.object(omr_admin.omr_dashboard, 'read_snapshot') as read:
        assert unauth_client.get('/dashboard/api/snapshot').status_code == 403
        read.assert_not_called()


def test_router_credentials_cannot_list_other_clients(user_client):
    with patch.object(omr_admin.omr_dashboard, 'read_snapshot') as read:
        assert user_client.get('/dashboard/api/snapshot').status_code == 403
        read.assert_not_called()


def test_readonly_router_credentials_are_not_dashboard_admin(ro_client):
    assert ro_client.get('/dashboard/api/snapshot').status_code == 403


def test_admin_reads_cached_snapshot_without_system_calls(admin_client):
    data={'schema_version':1, 'generated_at':1700000000, 'clients':[], 'warnings':[]}
    with patch.object(omr_admin.omr_dashboard, 'read_snapshot', return_value=data) as read:
        response=admin_client.get('/dashboard/api/snapshot')
    assert response.status_code == 200 and response.json() == data
    read.assert_called_once_with()
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-frame-options'] == 'DENY'


@pytest.mark.parametrize('method', ['post', 'put', 'delete', 'patch'])
def test_snapshot_has_no_write_operation(admin_client, method):
    assert admin_client.request(method.upper(), '/dashboard/api/snapshot').status_code == 405


@pytest.mark.parametrize('name', ['omr-admin-config.json', 'omr_dashboard.py', 'private.key'])
def test_assets_are_an_explicit_allowlist(unauth_client, name):
    assert unauth_client.get('/dashboard/assets/'+name).status_code == 404


def test_root_probe_remains_compatible(unauth_client):
    response=unauth_client.get('/')
    assert response.status_code == 200
    assert response.json() == 'Welcome to OpenMPTCProuter Server part'


@pytest.mark.parametrize('route,expected', [('/config',True),('/status',True),('/metrics/upload',True),('/dashboard/api/snapshot',False),('/docs',False)])
def test_only_router_api_calls_record_contact(route, expected):
    request=SimpleNamespace(url=SimpleNamespace(path=route))
    with patch.object(omr_admin.omr_dashboard, 'note_contact') as note:
        result=asyncio.run(omr_admin.get_current_user(token=make_token('openmptcprouter'),request=request))
    assert result.username == 'openmptcprouter'
    assert note.called is expected


def test_dashboard_storage_failure_cannot_break_router_authentication():
    request=SimpleNamespace(url=SimpleNamespace(path='/config'))
    with patch.object(omr_admin.omr_dashboard, 'note_contact', side_effect=OSError('unavailable')):
        result=asyncio.run(omr_admin.get_current_user(token=make_token('openmptcprouter'),request=request))
    assert result.username == 'openmptcprouter'
