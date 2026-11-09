"""Exercise the production route retirement helper without importing the API.

All ip commands are fixtures. The real host's routes are never accessed.
"""
import ast
import ipaddress
import json
import logging
from pathlib import Path
import re
import subprocess
import unittest
from unittest.mock import patch


def load_helper():
    source = Path(__file__).resolve().parents[1] / 'admin/omradmin.py'
    tree = ast.parse(source.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_remove_obsolete_lan_routes')
    namespace = dict(ipaddress=ipaddress, json=json, re=re, subprocess=subprocess, LOG=logging.getLogger('lan-retirement-test'))
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
    return namespace['_remove_obsolete_lan_routes']


class RouteRetirementTests(unittest.TestCase):
    def setUp(self):
        self.helper = load_helper()
        self.old = ['192.168.100.1/255.255.255.0']
        self.user = {'vpnremoteip': '10.255.220.2'}
        self.config = {'users': [{'openmptcprouter': {'lanips': ['10.1.1.1/23']}}]}
        self.route = {'dst': '192.168.100.0/24', 'gateway': '10.255.220.2', 'dev': 'mqvpn0'}

    def run_fixture(self, routes, config=None, old=None):
        def command(args, **kwargs):
            if args[:4] == ['ip', '-j', '-4', 'route']:
                return subprocess.CompletedProcess(args, 0, json.dumps(routes), '')
            return subprocess.CompletedProcess(args, 0, '', '')
        with patch('subprocess.run', side_effect=command) as calls:
            passed = self.helper(self.old if old is None else old, self.user, config or self.config)
        return passed, [c.args[0] for c in calls.call_args_list]

    def test_changed_lan_removes_exact_previous_route(self):
        passed, calls = self.run_fixture([self.route])
        self.assertTrue(passed)
        self.assertIn(['ip', '-4', 'route', 'del', '192.168.100.0/24', 'via', '10.255.220.2', 'dev', 'mqvpn0', 'table', 'main'], calls)

    def test_new_lan_route_is_preserved(self):
        passed, calls = self.run_fixture([self.route, dict(self.route, dst='10.1.0.0/23')])
        self.assertTrue(passed)
        self.assertEqual(len(calls), 2)

    def test_other_users_prefix_is_preserved(self):
        self.config['users'][0]['other'] = {'lanips': ['192.168.100.2/24']}
        passed, calls = self.run_fixture([self.route])
        self.assertTrue(passed)
        self.assertEqual(calls, [])

    def test_other_gateway_is_preserved(self):
        passed, calls = self.run_fixture([dict(self.route, gateway='10.255.220.3')])
        self.assertTrue(passed)
        self.assertEqual(len(calls), 1)

    def test_non_vpn_interface_is_preserved(self):
        passed, calls = self.run_fixture([dict(self.route, dev='ens192')])
        self.assertTrue(passed)
        self.assertEqual(len(calls), 1)

    def test_default_route_is_preserved(self):
        passed, calls = self.run_fixture([dict(self.route, dst='default')], old=['0.0.0.0/0'])
        self.assertTrue(passed)
        self.assertEqual(len(calls), 1)

    def test_default_route_does_not_prevent_stale_lan_cleanup(self):
        passed, calls = self.run_fixture([dict(self.route, dst='default'), self.route])
        self.assertTrue(passed)
        self.assertEqual(len(calls), 2)

    def test_numeric_default_route_is_preserved(self):
        passed, calls = self.run_fixture([dict(self.route, dst='0.0.0.0/0')], old=['0.0.0.0/0'])
        self.assertTrue(passed)
        self.assertEqual(len(calls), 1)

    def test_multiple_previous_prefixes_remove_only_obsolete(self):
        old = self.old + ['10.1.1.1/23']
        passed, calls = self.run_fixture([self.route, dict(self.route, dst='10.1.0.0/23')], old=old)
        self.assertTrue(passed)
        self.assertEqual(len(calls), 2)

    def test_read_failure_is_reported(self):
        with patch('subprocess.run', side_effect=OSError('fixture')):
            self.assertFalse(self.helper(self.old, self.user, self.config))

    def test_invalid_other_user_config_cannot_authorize_deletion(self):
        self.config['users'][0]['other'] = {'lanips': ['invalid']}
        with patch('subprocess.run') as calls:
            self.assertFalse(self.helper(self.old, self.user, self.config))
            calls.assert_not_called()

    def test_missing_previous_gateway_is_noop(self):
        with patch('subprocess.run') as calls:
            self.assertTrue(self.helper(self.old, {}, self.config))
            calls.assert_not_called()


if __name__ == '__main__':
    logging.disable(logging.CRITICAL)
    unittest.main(verbosity=2)
