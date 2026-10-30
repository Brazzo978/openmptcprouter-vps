"""Profile journal/rollback tests with disposable files and synthetic services."""
import copy
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import omr_profiles as profiles

try:
    import pytest
    pytestmark = pytest.mark.real_env
except ImportError:
    pass

TX = 'a' * 32
REQ = {'mptcp': {'scheduler': 'bpf_red', 'congestion_control': 'bbr'},
       'mqvpn': {'scheduler': 'minrtt', 'cc': 'bbr2'}}


class FakeRuntime:
    def __init__(self):
        self.value = {'mptcp': {'scheduler': 'default', 'congestion_control': 'cubic', 'nanbbr_aggressiveness': 50},
                      'mqvpn': {'scheduler': 'wlb', 'cc': 'bbr2', 'fec_enable': False,
                                'fec_scheme': 'xor', 'reinjection_control': False,
                                'reinjection_mode': 'default', 'reorder': {'enabled': 'off',
                                'max_wait_ms': 30, 'cap_packets': 1024}}}
        self.secrets = {'auth_key': 'fixture-secret-key', 'users': [{'key': 'fixture-user-key'}]}
        self.fail_apply = False
        self.fail_restore = False
        self.applies = self.restores = 0

    def current(self): return copy.deepcopy(self.value)
    def availability(self):
        return {'tcp_schedulers':['default','bpf_red'], 'tcp_cc':['bbr','cubic','nanbbr3_light'],
                'mq_schedulers':['wlb','minrtt'], 'mq_cc':['bbr2','bbr','cubic'],
                'fec_schemes':list(profiles.FEC_SCHEMES)}
    def validate(self, target):
        if target['mptcp']['scheduler'] not in self.availability()['tcp_schedulers']:
            raise profiles.ProfileError(409, 'Unavailable')
    def snapshot(self, target): return copy.deepcopy(self.value)
    def apply(self, target):
        self.applies += 1
        self.value['mptcp'].update(target['mptcp'])
        if self.fail_apply: raise RuntimeError('simulated partially applied change')
        self.value['mqvpn'].update(target['mqvpn'])
    def restore(self, old):
        self.restores += 1
        if self.fail_restore: raise RuntimeError('simulated rollback failure')
        self.value = copy.deepcopy(old)


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.clock = [1000.]
        self.runtime = FakeRuntime()
        self.manager = profiles.ProfileManager(self.runtime, root/'journal.json', root/'lock',
                    window=240, clock=lambda: self.clock[0], enable_timer=False,
                    monotonic=lambda:self.clock[0], boot_id=lambda:'fixture-boot')
    def tearDown(self): self.tmp.cleanup()

    def test_confirm_is_idempotent_and_journal_has_no_secrets(self):
        first = self.manager.apply(TX, REQ)
        self.assertEqual(first['state'], 'pending')
        self.assertEqual(first['seconds_remaining'], 240)
        self.clock[0] += 10
        self.assertEqual(self.manager.status(TX)['seconds_remaining'], 230)
        self.assertEqual(self.manager.apply(TX, REQ)['state'], 'pending')
        self.assertEqual(self.runtime.applies, 1)
        with self.assertRaises(profiles.ProfileError):
            self.manager.apply(TX, {'mptcp': REQ['mptcp'], 'mqvpn': {'scheduler': 'wlb', 'cc':'bbr2'}})
        self.assertEqual(self.manager.finish(TX, True)['state'], 'confirmed')
        self.assertEqual(self.manager.finish(TX, True)['state'], 'confirmed')
        raw = self.manager.journal.read_text()
        self.assertNotIn('fixture-secret-key', raw)
        self.assertNotIn('fixture-user-key', raw)
        self.assertEqual(stat.S_IMODE(self.manager.journal.stat().st_mode), 0o600)
        other = profiles.ProfileManager(self.runtime, self.manager.journal, self.manager.lock,
                                      clock=lambda: self.clock[0], enable_timer=False,
                                      monotonic=lambda:self.clock[0], boot_id=lambda:'fixture-boot')
        other.startup()
        self.assertEqual(other.status(TX)['state'], 'confirmed')

    def test_expired_pending_restores_after_api_restart(self):
        old = self.runtime.current()
        self.manager.apply(TX, REQ)
        self.clock[0] += 241
        restarted = profiles.ProfileManager(self.runtime, self.manager.journal, self.manager.lock,
                                            clock=lambda: self.clock[0], enable_timer=False,
                                            monotonic=lambda:self.clock[0], boot_id=lambda:'fixture-boot')
        restarted.startup()
        self.assertEqual(restarted.status(TX)['state'], 'rolled_back')
        self.assertEqual(self.runtime.current(), old)
        self.assertEqual(self.manager.finish(TX, False)['state'], 'rolled_back')

    def test_api_restart_during_partial_apply_restores_immediately(self):
        before = self.runtime.current()
        self.manager._write({'transaction': TX, 'state': 'applying', 'deadline': 1240,
                             'before': before, 'target': REQ})
        self.runtime.value['mptcp']['scheduler'] = 'bpf_red'
        self.manager.startup()
        self.assertEqual(self.manager.status(TX)['state'], 'rolled_back')
        self.assertEqual(self.runtime.current(), before)

    def test_ntp_clock_steps_do_not_change_rollback_time(self):
        wall, uptime = [1000.], [200.]
        self.manager.clock=lambda:wall[0]
        self.manager.monotonic=lambda:uptime[0]
        old=self.runtime.current()
        self.manager.apply(TX,REQ)
        wall[0] += 86400
        uptime[0] += 5
        status=self.manager.status(TX)
        self.assertEqual(status['state'],'pending')
        self.assertEqual(status['seconds_remaining'],235)
        wall[0] -= 172800
        uptime[0] += 236
        self.assertEqual(self.manager.status(TX)['state'],'rolled_back')
        self.assertEqual(self.runtime.current(),old)

    def test_reboot_rolls_back_pending_without_waiting_for_wall_clock(self):
        before=self.runtime.current()
        self.manager.apply(TX,REQ)
        restarted=profiles.ProfileManager(self.runtime,self.manager.journal,self.manager.lock,
            clock=lambda:self.clock[0],enable_timer=False,monotonic=lambda:0,boot_id=lambda:'other-boot')
        restarted.startup()
        self.assertEqual(restarted.status(TX)['state'],'rolled_back')
        self.assertEqual(self.runtime.current(),before)

    def test_api_restart_during_preflight_marks_transaction_rolled_back(self):
        before = self.runtime.current()
        self.manager._write({'transaction': TX, 'state': 'preparing', 'deadline': 1240,
                             'target': REQ})
        self.manager.startup()
        self.assertEqual(self.manager.status(TX)['state'], 'rolled_back')
        self.assertEqual(self.runtime.current(), before)
        self.assertEqual(self.runtime.restores, 0)

    def test_timed_out_apply_and_concurrent_rollback_cannot_create_late_change(self):
        ready, proceed = threading.Event(), threading.Event()
        validate = self.runtime.validate
        def slow_validate(target):
            ready.set()
            if not proceed.wait(3): raise RuntimeError('test synchronization timeout')
            validate(target)
        self.runtime.validate = slow_validate
        before = self.runtime.current()
        with ThreadPoolExecutor(max_workers=2) as pool:
            applying = pool.submit(self.manager.apply, TX, REQ)
            self.assertTrue(ready.wait(2))
            journal = json.loads(self.manager.journal.read_text())
            self.assertEqual(journal['transaction'], TX)
            self.assertEqual(journal['state'], 'preparing')
            self.assertNotIn('before', journal)
            rollback = pool.submit(self.manager.finish, TX, False)
            proceed.set()
            self.assertEqual(applying.result(timeout=3)['state'], 'pending')
            self.assertEqual(rollback.result(timeout=3)['state'], 'rolled_back')
        self.assertEqual(self.runtime.current(), before)
        self.assertEqual(self.manager.status(TX)['state'], 'rolled_back')

    def test_partial_apply_failure_restores_snapshot(self):
        before = self.runtime.current()
        self.runtime.fail_apply = True
        with self.assertRaises(profiles.ProfileError) as cm:self.manager.apply(TX, REQ)
        self.assertEqual(cm.exception.status, 503)
        self.assertEqual(self.runtime.current(), before)
        self.assertEqual(self.manager.status(TX)['state'], 'rolled_back')

    def test_failed_rollback_blocks_new_transaction_and_can_retry(self):
        self.manager.apply(TX, REQ)
        self.runtime.fail_restore = True
        with self.assertRaises(profiles.ProfileError): self.manager.finish(TX, False)
        self.assertEqual(self.manager.status(TX)['state'], 'rollback_failed')
        with self.assertRaises(profiles.ProfileError): self.manager.apply('b'*32, REQ)
        self.runtime.fail_restore = False
        self.assertEqual(self.manager.finish(TX, False)['state'], 'rolled_back')

    def test_legacy_mutations_are_locked_while_pending(self):
        self.manager.apply(TX, REQ)
        with self.assertRaises(profiles.ProfileError):
            with self.manager.guard_existing_mutation(): pass
        self.manager.finish(TX, True)
        with self.manager.guard_existing_mutation(): pass

    def test_two_concurrent_transactions_only_one_applies(self):
        barrier = threading.Barrier(2)
        def attempt(tx):
            barrier.wait()
            try: return self.manager.apply(tx, REQ)['state']
            except profiles.ProfileError as e: return e.status
        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(attempt, [TX, 'b'*32]))
        self.assertCountEqual(result, ['pending', 409])
        self.assertEqual(self.runtime.applies, 1)

    def test_invalid_id_and_unavailable_algorithm_never_mutate(self):
        with self.assertRaises(profiles.ProfileError): self.manager.status('../etc/passwd')
        with self.assertRaises(profiles.ProfileError):
            self.manager.apply(TX, {'mptcp': {'scheduler':'notinstalled','congestion_control':'bbr'},
                                    'mqvpn': {'scheduler':'wlb','cc':'bbr2'}})
        self.assertEqual(self.runtime.applies, 0)

    def test_unavailable_external_watchdog_refuses_any_change(self):
        def unavailable(): raise profiles.ProfileError(503, 'Watchdog unavailable')
        self.runtime.ensure_recovery_ready = unavailable
        with self.assertRaises(profiles.ProfileError) as error:
            self.manager.apply(TX, REQ)
        self.assertEqual(error.exception.status, 503)
        self.assertEqual(self.runtime.applies, 0)
        self.assertEqual(self.manager.status(TX)['state'], 'rolled_back')

    def test_lock_rejects_symlinks(self):
        victim = self.manager.lock.parent/'unrelated'
        victim.write_text('untouched')
        self.manager.lock.symlink_to(victim)
        with self.assertRaises(OSError): self.manager.status(TX)
        self.assertEqual(victim.read_text(), 'untouched')


class RuntimeTests(unittest.TestCase):
    def test_fec_schemes_are_advertised_only_for_verified_server_build(self):
        runtime=profiles.Runtime(lambda cmd:{'ok':True,'version':'0.16.2','scheduler':'wlb','fec_enabled':1},
                                 lambda cc:None,lambda:50)
        def read_text(path, *args, **kwargs):
            if str(path).endswith('available_schedulers'): return 'default bpf_red'
            if str(path).endswith('tcp_available_congestion_control'): return 'reno cubic bbr'
            raise FileNotFoundError(str(path))
        def run(cmd, **kwargs):
            if cmd[0]=='dpkg-query':
                return type('Completed',(),{'returncode':0,'stdout':package[0]})()
            return type('Completed',(),{'returncode':1,'stdout':''})()
        with patch.object(Path,'read_text',autospec=True,side_effect=read_text), \
             patch.object(profiles.subprocess,'run',side_effect=run), \
             patch.object(profiles,'_sha256_file',return_value=profiles.VERIFIED_FEC_BINARIES['0.16.2-3k2']) as digest:
            package=['0.16.2-3k2']
            availability=runtime.availability()
            self.assertEqual(set(availability['fec_schemes']),set(profiles.FEC_SCHEMES))
            self.assertIn('backup_fec',availability['mq_schedulers'])
            package[0]='0.16.2-1'
            availability=runtime.availability()
            self.assertEqual(availability['fec_schemes'],[])
            self.assertNotIn('backup_fec',availability['mq_schedulers'])
            package[0]='0.16.2-3k2'
            digest.return_value='modified-binary'
            self.assertEqual(runtime.availability()['fec_schemes'],[])

    def test_partial_mq_changes_preserve_users_keys_ports_and_other_reorder_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'server.json'
            config = {'mode':'server', 'listen':'0.0.0.0:65443', 'auth_key':'secret',
                      'users':[{'name':'router','key':'user-key','fixed_ip':'10.0.0.2'}],
                      'scheduler':'wlb', 'cc':'bbr2', 'reorder':{'enabled':'auto','other':123},
                      'reorder_rules':[{'proto':'udp','port':443}]}
            path.write_text(json.dumps(config)); path.chmod(0o600)
            def control(cmd): return {'ok':True, 'scheduler':json.loads(path.read_text())['scheduler'], 'fec_enabled':1}
            runtime = profiles.Runtime(control, lambda cc: None, lambda:50, mq_config=str(path))
            saved={'scheduler':{'present':True,'value':'wlb'},
                   'reorder':{'parent_present':True,'fields':{'enabled':{'present':True,'value':'auto'}}}}
            with patch.object(profiles.subprocess,'run') as run:
                runtime._set_mq({'scheduler':'minrtt','reorder':{'enabled':'off'}})
                actual=json.loads(path.read_text())
                self.assertEqual(actual['auth_key'],config['auth_key'])
                self.assertEqual(actual['users'],config['users'])
                self.assertEqual(actual['listen'],config['listen'])
                self.assertEqual(actual['reorder_rules'],config['reorder_rules'])
                self.assertEqual(actual['reorder']['other'],123)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
                runtime._set_mq(saved,restore=True)
            self.assertEqual(json.loads(path.read_text()),config)
            self.assertEqual(run.call_count,4)  # restart plus is-active, each direction

    def test_sysctl_rewrite_keeps_unmanaged_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'sysctl.conf'
            path.write_text('# managed elsewhere\nnet.ipv4.ip_forward=1\nnet.mptcp.scheduler=default\n')
            profiles._rewrite_sysctl(str(path),['net.mptcp.scheduler'],['net.mptcp.scheduler=bpf_red\n'])
            self.assertIn('net.ipv4.ip_forward=1\n',path.read_text())
            profiles._rewrite_sysctl(str(path),['net.mptcp.scheduler'],['net.mptcp.scheduler=default\n'])
            self.assertEqual(path.read_text(),'# managed elsewhere\nnet.ipv4.ip_forward=1\nnet.mptcp.scheduler=default\n')

    def test_real_runtime_transaction_and_partial_failure_restore_all_managed_fields(self):
        for fail_restart in (False, True):
            with self.subTest(fail_restart=fail_restart), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                mq = root/'server.json'
                config = {'listen':'127.0.0.1:65443','auth_key':'private-value',
                          'users':[{'name':'fixture','key':'private-user','fixed_ip':'10.0.0.2'}],
                          'scheduler':'wlb','cc':'bbr2','path_policy':[{'weight':9}],
                          'reorder':{'enabled':'auto','max_wait_ms':80,'cap_packets':2048,'unrelated':17},
                          'reorder_rules':[{'port':443,'proto':'udp'}]}
                mq.write_text(json.dumps(config));mq.chmod(0o600)
                sysconf=root/'sysctl.conf'
                sysconf.write_text('net.ipv4.ip_forward=1\nnet.mptcp.scheduler=default\nnet.ipv4.tcp_congestion_control=cubic\n')
                nan=root/'nan.json'; nan.write_text('{"version":1,"aggressiveness":75,"unrelated":"retain"}')
                params={}
                for cc,value in zip(('nanbbr1_var','nanbbr2_var','nanbbr3_var'),('70','75','80')):
                    params[cc]=root/cc;params[cc].write_text(value)
                live={'net.mptcp.scheduler':'default','net.ipv4.tcp_congestion_control':'cubic',
                      'net.ipv4.tcp_available_congestion_control':'cubic bbr nanbbr3_light'}
                def sysctl(key, value=None):
                    if value is not None: live[key]=str(value);return ''
                    return live[key]
                def control(_):
                    return {'ok':True,'scheduler':json.loads(mq.read_text())['scheduler'],'fec_enabled':1}
                runtime=profiles.Runtime(control, lambda cc:str(params[cc]),
                    lambda:json.loads(nan.read_text())['aggressiveness'],mq_config=str(mq),
                    sysctl_file=str(sysconf),nanbbr_file=str(nan))
                runtime.availability=lambda:{'tcp_schedulers':['default','bpf_red'],
                    'tcp_cc':['cubic','bbr','nanbbr3_light'],'mq_schedulers':['wlb','minrtt'],
                    'mq_cc':['bbr2'],'fec_schemes':['xor']}
                runtime.ensure_recovery_ready=lambda:None
                manager=profiles.ProfileManager(runtime,root/'journal',root/'lock',
                                                  clock=lambda:1000,enable_timer=False)
                request={'mptcp':{'scheduler':'bpf_red','congestion_control':'nanbbr3_light',
                                  'nanbbr_aggressiveness':50},
                         'mqvpn':{'scheduler':'minrtt','cc':'bbr2','fec_enable':True,
                                  'fec_scheme':'xor','reorder':{'enabled':'on','max_wait_ms':30}}}
                calls=[]
                did_fail=[False]
                def run(cmd,**kwargs):
                    calls.append(cmd)
                    if fail_restart and cmd==['systemctl','restart','mqvpn'] and not did_fail[0]:
                        did_fail[0]=True
                        raise profiles.subprocess.CalledProcessError(1,cmd)
                    # No unrelated dependent service is running in this lab.
                    rc=3 if cmd[:3]==['systemctl','is-active','--quiet'] and cmd[-1]!='mqvpn' else 0
                    return type('Completed',(),{'returncode':rc})()
                with patch.object(profiles,'_scheduler_key',return_value='net.mptcp.scheduler'), \
                     patch.object(profiles,'_sysctl',side_effect=sysctl), \
                     patch.object(profiles.subprocess,'run',side_effect=run):
                    if fail_restart:
                        with self.assertRaises(profiles.ProfileError): manager.apply(TX,request)
                    else:
                        self.assertEqual(manager.apply(TX,request)['state'],'pending')
                        changed=json.loads(mq.read_text())
                        self.assertEqual(changed['users'],config['users'])
                        self.assertEqual(changed['auth_key'],config['auth_key'])
                        self.assertEqual(changed['path_policy'],config['path_policy'])
                        self.assertEqual(changed['reorder_rules'],config['reorder_rules'])
                        self.assertEqual(manager.finish(TX,False)['state'],'rolled_back')
                self.assertEqual(json.loads(mq.read_text()),config)
                self.assertEqual(live['net.mptcp.scheduler'],'default')
                self.assertEqual(live['net.ipv4.tcp_congestion_control'],'cubic')
                self.assertIn('net.ipv4.ip_forward=1\n',sysconf.read_text())
                self.assertEqual(json.loads(nan.read_text()),{'version':1,'aggressiveness':75,'unrelated':'retain'})
                self.assertEqual([p.read_text() for p in params.values()],['70','75','80'])
                self.assertEqual(manager.status(TX)['state'],'rolled_back')

if __name__=='__main__': unittest.main(verbosity=2)
