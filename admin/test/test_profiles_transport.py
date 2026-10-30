"""Cross-transport profile transactions with synthetic, private test data."""
import copy
import json
from pathlib import Path
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
import omr_profiles as p

pytestmark = pytest.mark.real_env
TX = 'b' * 32
OLD = {'transport':'glorytun_tcp', 'proxy':'none',
       'mptcp':{'scheduler':'bpf_red', 'congestion_control':'bbr'}}
NO_TUNNEL = {'transport':'none', 'proxy':'shadowsocks-rust',
             'mptcp':{'scheduler':'default', 'congestion_control':'bbr'}}


@pytest.fixture
def lab(tmp_path, monkeypatch):
    config = tmp_path/'config.json'
    config.write_text(json.dumps({'users':[{'openmptcprouter':{
        'userid':0, 'vpn':'mqvpn', 'proxy':'shadowsocks-rust', 'vpnremoteip':'10.255.220.2',
        'fw_ports':[{'name':'web','port':'8080','proto':'tcp','fwtype':'DNAT','family':4,'vpn':'default'}],
        'shadowsocks-go':{'port':65280,'protocol':'2022-blake3-aes-256-gcm','password':'ss-private:ss-user-private'},
        'key':'primary-private'},
        'second':{'userid':7, 'vpn':'mqvpn', 'key':'other-private'}}],
        'private_global':'global-secret'}))
    mq=tmp_path/'mq.json'
    mq.write_text(json.dumps({'scheduler':'wlb','cc':'bbr2','auth_key':'mq-secret',
        'users':[{'name':'openmptcprouter','key':'mq-user-secret','fixed_ip':'10.255.220.2'}]}))
    vpn=tmp_path/'current-vpn';vpn.write_text('mqvpn\n')
    proxy=tmp_path/'current-proxy';proxy.write_text('shadowsocks-rust\n')
    glory=tmp_path/'glory';glory.write_text('MPTCP=true\n')
    (tmp_path/'glory.key').write_text('glory-private')
    ssusers=tmp_path/'ssusers.json';ssusers.write_text(json.dumps({'openmptcprouter':'ss-user-private'}))
    ssgo=tmp_path/'ssgo.json';ssgo.write_text(json.dumps({'servers':[{'name':'ss-2022','uPSKStorePath':str(ssusers),
        'protocol':'2022-blake3-aes-256-gcm','psk':'ss-private',
        'tcpListeners':[{'network':'tcp','multipath':True,'address':':65280'}]}]}))
    sysconf=tmp_path/'sysctl';sysconf.write_text('net.mptcp.scheduler=default\nnet.ipv4.tcp_congestion_control=cubic\n')
    live={'net.mptcp.scheduler':'default','net.ipv4.tcp_congestion_control':'cubic',
          'net.ipv4.tcp_available_congestion_control':'cubic bbr'}
    def sysctl(name,value=None):
        if value is not None:live[name]=str(value);return ''
        return live[name]
    monkeypatch.setattr(p,'_sysctl',sysctl)
    monkeypatch.setattr(p,'_scheduler_key',lambda:'net.mptcp.scheduler')
    monkeypatch.setattr(p,'_restore_scheduler',lambda value:live.update({'net.mptcp.scheduler':value}))
    monkeypatch.setattr(p,'_restart_mptcp_dependents',lambda:None)
    service_calls=[]
    def run(args,**kwargs):
        service_calls.append(args)
        return subprocess.CompletedProcess(args,0,'LISTEN configured' if args[0]=='ss' else '','')
    monkeypatch.setattr(p.subprocess,'run',run)
    def control(_):
        return {'ok':True,'version':'0.16.2','scheduler':json.loads(mq.read_text())['scheduler']}
    runtime=p.Runtime(control,lambda _:None,lambda:None,mq_config=str(mq),sysctl_file=str(sysconf),
        admin_config=str(config),vpn_file=str(vpn),proxy_file=str(proxy),glory_config=str(glory),
        config_lock=str(tmp_path/'config.lock'),ss_go_config=str(ssgo),ss_go_users=str(ssusers),
        ss_libev_config=str(tmp_path/'libev.json'))
    runtime.availability=lambda:{'tcp_schedulers':['default','bpf_red'],'tcp_cc':['bbr','cubic'],
        'mq_schedulers':['wlb','minrtt'],'mq_cc':['bbr2'],'fec_schemes':[],
        'transports':['mqvpn','glorytun_tcp','none'],'proxies':['none','shadowsocks-rust'],
        'tcp_proxies':['shadowsocks-rust']}
    runtime.ensure_recovery_ready=lambda _:None
    manager=p.ProfileManager(runtime,tmp_path/'journal',tmp_path/'profile.lock',enable_timer=False)
    return manager,runtime,live,service_calls


def test_glorytun_transaction_preserves_credentials_other_users_and_rolls_back(lab):
    manager,runtime,live,calls=lab
    before=json.loads(Path(runtime.admin_config).read_text())
    mq_before=Path(runtime.mq_config).read_bytes()
    assert manager.apply(TX,copy.deepcopy(OLD))['state']=='pending'
    after=json.loads(Path(runtime.admin_config).read_text())
    assert after['users'][0]['openmptcprouter']['vpn']=='glorytun_tcp'
    assert after['users'][0]['openmptcprouter']['proxy']=='none'
    assert after['users'][0]['second']==before['users'][0]['second']
    assert after['users'][0]['openmptcprouter']['key']==before['users'][0]['openmptcprouter']['key']
    assert after['private_global']==before['private_global']
    assert Path(runtime.vpn_file).read_text()=='glorytun_tcp\n'
    assert Path(runtime.proxy_file).read_text()=='none\n'
    assert Path(runtime.mq_config).read_bytes()==mq_before
    assert not any('mqvpn' in call for call in calls)
    journal=manager.journal.read_text()
    for secret in ('primary-private','other-private','global-secret','glory-private','mq-secret','ss-user-private'):
        assert secret not in journal
    assert manager.finish(TX,False)['state']=='rolled_back'
    assert json.loads(Path(runtime.admin_config).read_text())==before
    assert Path(runtime.vpn_file).read_text()=='mqvpn\n'
    assert Path(runtime.proxy_file).read_text()=='shadowsocks-rust\n'
    assert Path(runtime.mq_config).read_bytes()==mq_before
    assert live['net.mptcp.scheduler']=='default' and live['net.ipv4.tcp_congestion_control']=='cubic'


def test_glorytun_does_not_depend_on_running_mqvpn(lab):
    manager,runtime,live,calls=lab
    Path(runtime.mq_config).unlink()
    runtime.control_api=lambda _: (_ for _ in ()).throw(p.ProfileError(503,'MQVPN down'))
    assert manager.apply(TX,copy.deepcopy(OLD))['state']=='pending'
    assert manager.finish(TX,False)['state']=='rolled_back'
    assert not any('mqvpn' in call for call in calls)


def test_no_tunnel_clears_target_without_mqvpn_and_rollback_restores_it(lab):
    manager,runtime,live,calls=lab
    before=json.loads(Path(runtime.admin_config).read_text())
    Path(runtime.mq_config).unlink()
    runtime.control_api=lambda _: (_ for _ in ()).throw(p.ProfileError(503,'MQVPN down'))
    assert manager.apply(TX,copy.deepcopy(NO_TUNNEL))['state']=='pending'
    with pytest.raises(p.ProfileError,match='route before confirming'):manager.finish(TX,True)
    with pytest.raises(p.ProfileError,match='selected transport'):manager.route(TX,'10.255.220.2')
    result=manager.route(TX,no_tunnel=True)
    assert result['route_ready'] and result['no_tunnel']
    assert manager.route(TX,no_tunnel=True)==result
    assert manager.status(TX)['route_no_tunnel'] is True
    assert runtime.current()['selection']['vpnremoteip'] is None
    user=json.loads(Path(runtime.admin_config).read_text())['users'][0]['openmptcprouter']
    assert user['vpn']=='none' and user['proxy']=='shadowsocks-rust' and 'vpnremoteip' not in user
    assert manager.finish(TX,False)['state']=='rolled_back'
    assert json.loads(Path(runtime.admin_config).read_text())==before
    assert not any('mqvpn' in call for call in calls)


def test_no_tunnel_clear_rejects_wrong_transport_or_stopped_proxy(lab,monkeypatch):
    manager,runtime,live,calls=lab
    manager.apply(TX,copy.deepcopy(OLD))
    with pytest.raises(p.ProfileError,match='selected transport'):manager.route(TX,no_tunnel=True)
    manager.finish(TX,False)
    manager.apply('c'*32,copy.deepcopy(NO_TUNNEL))
    monkeypatch.setattr(runtime,'_proxy_active',lambda _:False)
    with pytest.raises(p.ProfileError,match='service is not ready'):manager.route('c'*32,no_tunnel=True)
    assert json.loads(Path(runtime.admin_config).read_text())['users'][0]['openmptcprouter']['vpnremoteip']=='10.255.220.2'


@pytest.mark.parametrize('original',['absent','null'])
def test_no_tunnel_interruption_recovers_and_preserves_previous_target_presence(lab,original):
    manager,runtime,live,calls=lab
    doc=json.loads(Path(runtime.admin_config).read_text())
    if original=='absent':doc['users'][0]['openmptcprouter'].pop('vpnremoteip')
    else:doc['users'][0]['openmptcprouter']['vpnremoteip']=None
    Path(runtime.admin_config).write_text(json.dumps(doc))
    manager.apply(TX,copy.deepcopy(NO_TUNNEL))
    state=manager._load();state['route']={'state':'applying','no_tunnel':True}
    state['before']['route_touched']=True;manager._write(state)
    runtime.apply_route('none',None);manager.startup()
    assert manager.status(TX)['state']=='rolled_back'
    user=json.loads(Path(runtime.admin_config).read_text())['users'][0]['openmptcprouter']
    assert ('vpnremoteip' in user)==(original=='null')
    if original=='null':assert user['vpnremoteip'] is None


def test_no_tunnel_capability_depends_on_active_proxy_not_mqvpn(lab,monkeypatch):
    manager,runtime,live,calls=lab
    runtime.control_api=lambda _: (_ for _ in ()).throw(p.ProfileError(503,'MQVPN down'))
    monkeypatch.setattr(runtime,'_mq_attested',lambda:False)
    monkeypatch.setattr(runtime,'_glory_ready',lambda:False)
    runtime.availability=p.Runtime.availability.__get__(runtime,p.Runtime)
    available=runtime.availability()
    assert available['transports']==['none'] and 'shadowsocks-rust' in available['tcp_proxies']
    assert available['mq_schedulers']==[] and not available['mq_running']
    monkeypatch.setattr(runtime,'_tcp_listening',lambda _:False)
    assert 'none' not in runtime.availability()['transports']


@pytest.mark.parametrize('fault',['multipath','listen','protocol','credentials','service','socket','loopback','user_store'])
def test_rust_alias_requires_compatible_active_mptcp_go_endpoint(lab,monkeypatch,fault):
    manager,runtime,live,calls=lab
    assert runtime._proxy_active('shadowsocks-rust')
    config=json.loads(Path(runtime.ss_go_config).read_text())
    listener=config['servers'][0]['tcpListeners'][0]
    if fault=='multipath':listener['multipath']=False
    if fault=='listen':listener['network']='udp'
    if fault=='protocol':config['servers'][0]['protocol']='unsupported'
    if fault=='user_store':config['servers'][0]['uPSKStorePath']='/tmp/other-users.json'
    if fault=='credentials':Path(runtime.ss_go_users).write_text(json.dumps({'openmptcprouter':'mismatched'}))
    if fault=='loopback':listener['address']='127.0.0.1:65280'
    Path(runtime.ss_go_config).write_text(json.dumps(config))
    if fault in ('service','socket'):
        def run(args,**kwargs):
            if fault=='service' and args[0]=='systemctl':return subprocess.CompletedProcess(args,3,'','')
            if fault=='socket' and args[0]=='ss':return subprocess.CompletedProcess(args,0,'','')
            return subprocess.CompletedProcess(args,0,'LISTEN configured','')
        monkeypatch.setattr(p.subprocess,'run',run)
    assert not runtime._proxy_active('shadowsocks-rust')


def test_libev_is_advertised_as_its_own_proxy_not_rust_alias(lab,monkeypatch):
    manager,runtime,live,calls=lab
    Path(runtime.ss_go_config).unlink()
    doc=json.loads(Path(runtime.admin_config).read_text())
    doc['users'][0]['openmptcprouter']['shadowsocks_port']=65101
    Path(runtime.admin_config).write_text(json.dumps(doc))
    Path(runtime.ss_libev_config).write_text(json.dumps({'mptcp':True,'mode':'tcp_and_udp',
                                                          'port_key':{'65101':'libev-private'}}))
    runtime.availability=p.Runtime.availability.__get__(runtime,p.Runtime)
    available=runtime.availability()
    assert 'shadowsocks' in available['tcp_proxies'] and 'none' in available['transports']
    assert 'shadowsocks-rust' not in available['tcp_proxies']
    data=json.loads(Path(runtime.ss_libev_config).read_text());data['mptcp']=False
    Path(runtime.ss_libev_config).write_text(json.dumps(data))
    assert not runtime._proxy_active('shadowsocks')


def test_stopped_mqvpn_is_started_for_profile_and_stopped_on_rollback(lab,monkeypatch):
    manager,runtime,live,calls=lab
    active=[False];service_calls=[]
    def run(args,**kwargs):
        service_calls.append(args)
        if args==['systemctl','is-active','--quiet','mqvpn']:
            return subprocess.CompletedProcess(args,0 if active[0] else 3,'','')
        if args[:2] in (['systemctl','start'],['systemctl','restart']) and args[-1]=='mqvpn':active[0]=True
        if args==['systemctl','stop','mqvpn']:active[0]=False
        return subprocess.CompletedProcess(args,0,'','')
    monkeypatch.setattr(p.subprocess,'run',run)
    def control(_):
        if not active[0]:raise p.ProfileError(503,'service stopped')
        return {'ok':True,'version':'0.16.2','scheduler':json.loads(Path(runtime.mq_config).read_text())['scheduler']}
    runtime.control_api=control
    request={'transport':'mqvpn','proxy':'shadowsocks-rust',
             'mptcp':{'scheduler':'default','congestion_control':'bbr'},
             'mqvpn':{'scheduler':'minrtt','cc':'bbr2'}}
    assert manager.apply(TX,request)['state']=='pending' and active[0]
    assert manager.finish(TX,False)['state']=='rolled_back' and not active[0]
    assert ['systemctl','stop','mqvpn'] in service_calls
    assert json.loads(Path(runtime.mq_config).read_text())['scheduler']=='wlb'


def test_stopped_mqvpn_capabilities_require_attested_package(lab,monkeypatch):
    manager,runtime,live,calls=lab
    runtime.control_api=lambda _: (_ for _ in ()).throw(p.ProfileError(503,'service stopped'))
    def run(args,**kwargs):
        if args[0]=='dpkg-query':return subprocess.CompletedProcess(args,0,'0.16.2-3k2','')
        if args[:3]==['systemctl','is-active','--quiet']:
            return subprocess.CompletedProcess(args,3,'','')
        return subprocess.CompletedProcess(args,1,'','')
    monkeypatch.setattr(p.subprocess,'run',run)
    runtime.availability=p.Runtime.availability.__get__(runtime,p.Runtime)
    monkeypatch.setattr(p,'_sha256_file',lambda _:p.VERIFIED_FEC_BINARIES['0.16.2-3k2'])
    found=runtime.availability()
    assert 'mqvpn' in found['transports'] and 'wlb' in found['mq_schedulers']
    assert 'bbr2' in found['mq_cc'] and found['mq_running'] is False
    monkeypatch.setattr(p,'_sha256_file',lambda _:'0'*64)
    unknown=runtime.availability()
    assert 'mqvpn' not in unknown['transports'] and unknown['mq_schedulers']==[] and unknown['mq_cc']==[]


def test_partial_selector_write_failure_restores_previous_selection(lab,monkeypatch):
    manager,runtime,live,calls=lab
    before=json.loads(Path(runtime.admin_config).read_text())
    original=p._atomic_bytes;failed=[]
    def fail_once(filename,*args,**kwargs):
        if str(filename)==runtime.proxy_file and not failed:
            failed.append(True);raise OSError('simulated failure')
        return original(filename,*args,**kwargs)
    monkeypatch.setattr(p,'_atomic_bytes',fail_once)
    with pytest.raises(p.ProfileError):manager.apply(TX,copy.deepcopy(OLD))
    assert manager.status(TX)['state']=='rolled_back'
    assert json.loads(Path(runtime.admin_config).read_text())==before
    assert Path(runtime.vpn_file).read_text()=='mqvpn\n'
    assert Path(runtime.proxy_file).read_text()=='shadowsocks-rust\n'


def test_route_requires_expected_tunnel_address_and_restores_target(lab):
    manager,runtime,live,calls=lab
    manager.apply(TX,copy.deepcopy(OLD))
    with pytest.raises(p.ProfileError,match='route before confirming'):
        manager.finish(TX,True)
    with pytest.raises(p.ProfileError,match='does not match'):
        manager.route(TX,'10.255.220.2')
    assert manager.route(TX,'10.255.255.2')['route_ready']
    assert manager.route(TX,'10.255.255.2')['route_ready']
    assert json.loads(Path(runtime.admin_config).read_text())['users'][0]['openmptcprouter']['vpnremoteip']=='10.255.255.2'
    assert ['/usr/sbin/nft','-f','-'] in calls and ['/usr/local/sbin/wg-remote-lan-route'] in calls
    assert manager.finish(TX,False)['state']=='rolled_back'
    assert json.loads(Path(runtime.admin_config).read_text())['users'][0]['openmptcprouter']['vpnremoteip']=='10.255.220.2'
    assert sum(call==['/usr/sbin/nft','-f','-'] for call in calls)==2
    assert sum(call==['/usr/local/sbin/wg-remote-lan-route'] for call in calls)==2


def test_route_rejects_a_selected_vpn_service_that_stopped(lab,monkeypatch):
    manager,runtime,live,calls=lab
    manager.apply(TX,copy.deepcopy(OLD))
    monkeypatch.setattr(runtime,'_glory_ready',lambda:False)
    with pytest.raises(p.ProfileError,match='service is not ready'):
        manager.route(TX,'10.255.255.2')
    assert manager.status(TX)['route_ready'] is False
    assert json.loads(Path(runtime.admin_config).read_text())['users'][0]['openmptcprouter']['vpnremoteip']=='10.255.220.2'


def test_interrupted_route_is_rolled_back_at_watchdog_startup(lab):
    manager,runtime,live,calls=lab
    manager.apply(TX,copy.deepcopy(OLD))
    state=manager._load()
    state['route']={'state':'applying','remote':'10.255.255.2'}
    state['before']['route_touched']=True
    manager._write(state)
    runtime.apply_route('glorytun_tcp','10.255.255.2')
    manager.startup()
    assert manager.status(TX)['state']=='rolled_back'
    assert json.loads(Path(runtime.admin_config).read_text())['users'][0]['openmptcprouter']['vpnremoteip']=='10.255.220.2'


def test_confirm_v2_only_after_route_update_and_idempotent_replay(lab):
    manager,runtime,live,calls=lab
    manager.apply(TX,copy.deepcopy(OLD))
    manager.route(TX,'10.255.255.2')
    assert manager.finish(TX,True)['state']=='confirmed'
    assert manager.finish(TX,True)['state']=='confirmed'


def test_mqvpn_expected_fixed_address_is_verified(lab):
    manager,runtime,live,calls=lab
    assert runtime.expected_remote('mqvpn')=='10.255.220.2'
    data=json.loads(Path(runtime.mq_config).read_text())
    data['users'][0]['fixed_ip']='192.168.1.5'
    Path(runtime.mq_config).write_text(json.dumps(data))
    with pytest.raises(p.ProfileError):runtime.expected_remote('mqvpn')


def test_mqvpn_to_glorytun_and_back_restores_forwarding_target(lab):
    manager,runtime,live,calls=lab
    manager.apply(TX,copy.deepcopy(OLD));manager.route(TX,'10.255.255.2');manager.finish(TX,True)
    back={'transport':'mqvpn','proxy':'shadowsocks-rust',
          'mptcp':{'scheduler':'default','congestion_control':'bbr'},
          'mqvpn':{'scheduler':'wlb','cc':'bbr2'}}
    next_tx='c'*32
    manager.apply(next_tx,back);manager.route(next_tx,'10.255.220.2');manager.finish(next_tx,True)
    user=json.loads(Path(runtime.admin_config).read_text())['users'][0]['openmptcprouter']
    assert (user['vpn'],user['proxy'],user['vpnremoteip'])==('mqvpn','shadowsocks-rust','10.255.220.2')
    assert Path(runtime.vpn_file).read_text()=='mqvpn\n'
    assert Path(runtime.proxy_file).read_text()=='shadowsocks-rust\n'


def test_failed_route_refresh_restores_previous_target_and_retries_firewall(lab,monkeypatch):
    manager,runtime,live,calls=lab
    manager.apply(TX,copy.deepcopy(OLD))
    old_run=p.subprocess.run;failed=[]
    def fail_once(args,**kwargs):
        if args==['/usr/local/sbin/wg-remote-lan-route'] and not failed:
            failed.append(True);raise subprocess.CalledProcessError(1,args)
        return old_run(args,**kwargs)
    monkeypatch.setattr(p.subprocess,'run',fail_once)
    with pytest.raises(p.ProfileError,match='previous settings restored'):
        manager.route(TX,'10.255.255.2')
    assert manager.status(TX)['state']=='rolled_back'
    user=json.loads(Path(runtime.admin_config).read_text())['users'][0]['openmptcprouter']
    assert (user['vpn'],user['proxy'],user['vpnremoteip'])==('mqvpn','shadowsocks-rust','10.255.220.2')
    assert sum(call==['/usr/sbin/nft','-f','-'] for call in calls)==2


def test_forwarding_refresh_preserves_explicit_other_user_and_untouched_chains(lab,monkeypatch):
    manager,runtime,live,calls=lab
    doc=json.loads(Path(runtime.admin_config).read_text())
    primary=doc['users'][0]['openmptcprouter'];other=doc['users'][0]['second']
    primary['vpnremoteip']='10.255.255.2'
    primary['fw_ports'][0].update({'source_dip':'203.0.113.5','dest_ip':'198.51.100.9'})
    primary['fw_ports'].append({'name':'explicit','port':'9000','proto':'udp','fwtype':'DNAT',
                                'family':4,'vpn':'10.255.250.2'})
    primary['fw_ports'].append({'name':'service','port':'65100','proto':'tcp','fwtype':'ACCEPT','family':4})
    other['vpnremoteip']='10.255.220.9'
    other['fw_ports']=[{'name':'other','port':'9090','proto':'udp','fwtype':'DNAT','family':4,'vpn':'default'}]
    doc['bulk_redirect_v4']=False
    Path(runtime.admin_config).write_text(json.dumps(doc))
    scripts=[]
    def capture(args,**kwargs):
        if args==['/usr/sbin/nft','-f','-']:scripts.append(kwargs['input'])
        return subprocess.CompletedProcess(args,0,'','')
    monkeypatch.setattr(p.subprocess,'run',capture)
    runtime._refresh_forwarding()
    assert len(scripts)==1
    lines=scripts[0].splitlines()
    assert [x for x in lines if x.startswith('flush chain')]==[
        'flush chain inet omr user_accept','flush chain inet omr user_dnat']
    assert any('ip daddr 203.0.113.5 ip saddr 198.51.100.9 tcp dport 8080 dnat ip to 10.255.255.2' in x for x in lines)
    assert any('udp dport 9000 dnat ip to 10.255.250.2' in x for x in lines)
    assert any('udp dport 9090 dnat ip to 10.255.220.9' in x for x in lines)
    assert any('tcp dport 65100 accept' in x for x in lines)
    assert not any('1-64999' in x for x in lines)
    assert not any(name in x for x in lines for name in ('rpf_dnat_bypass','custom_dnat_bypass','dscp_mark','gre_snat'))
    assert json.loads(Path(runtime.admin_config).read_text())==doc


def test_config_writer_lock_preserves_concurrent_other_user_changes(lab):
    manager,runtime,live,calls=lab
    started=threading.Event()
    def selection():
        started.set();runtime._set_selection('glorytun_tcp','none')
    with ThreadPoolExecutor(max_workers=1) as pool:
        with p.configuration_lock(runtime.config_lock):
            pending=pool.submit(selection)
            assert started.wait(2)
            doc=json.loads(Path(runtime.admin_config).read_text())
            doc['users'][0]['second']['new_setting']='preserved'
            p._write_json(runtime.admin_config,doc)
            assert not pending.done()
        pending.result(timeout=3)
    after=json.loads(Path(runtime.admin_config).read_text())
    assert after['users'][0]['second']['new_setting']=='preserved'
    assert after['users'][0]['openmptcprouter']['vpn']=='glorytun_tcp'


@pytest.mark.parametrize('config,active,expected',[
    ('MPTCP=true\n',True,True),('MPTCP=1\n',True,True),
    ('MPTCP=\n',True,False),('MPTCP=true\nMPTCP=\n',True,False),
    ('MPTCP=true\n',False,False),
])
def test_glorytun_requires_installed_config_key_mptcp_and_active_service(lab,monkeypatch,config,active,expected):
    manager,runtime,live,calls=lab
    Path(runtime.glory_config).write_text(config)
    monkeypatch.setattr(p.subprocess,'run',lambda args,**kwargs:subprocess.CompletedProcess(args,0 if active else 3,'',''))
    assert runtime._glory_ready() is expected
    Path(str(runtime.glory_config)+'.key').unlink()
    assert not runtime._glory_ready()
