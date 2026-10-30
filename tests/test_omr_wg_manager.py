"""Isolated peer-manager tests. Keys and paths are synthetic; no live VPS state."""
import base64
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import omr_wg_manager as mod

def key(n): return base64.b64encode(bytes([n])*32).decode()

class FakeSystem:
    def __init__(self):
        self.live={key(1):'10.255.246.2'};self.next=10;self.calls=[]
        self.grants=[];self.restricted=[];self.lan_dest=[];self.fail_next_add=False;self.fail_policy=False
    def __call__(self,args,**kwargs):
        self.calls.append(list(args));out='';code=0
        if args[:3]==['wg','show','client-wg0']:
            field=args[3]
            if field=='allowed-ips':out=''.join(f'{k}\t{ip}/32\n' for k,ip in self.live.items())
            elif field=='public-key':out=key(201)+'\n'
            elif field=='latest-handshakes':out=''.join(f'{k}\t{int(time.time())-10}\n' for k in self.live)
            elif field=='transfer':out=''.join(f'{k}\t123\t456\n' for k in self.live)
        elif args==['wg','genkey']:
            self.next+=1;out=key(self.next)+'\n'
        elif args==['wg','pubkey']:
            raw=kwargs.get('input','').encode()
            out=(key(1) if raw.decode().strip()==key(2) else base64.b64encode(hashlib.sha256(raw).digest()).decode())+'\n'
        elif args[:4]==['wg','set','client-wg0','peer']:
            if args[5]=='remove':self.live.pop(args[4],None)
            elif self.fail_next_add:self.fail_next_add=False;code=1
            else:self.live[args[4]]=args[6].removesuffix('/32')
        elif args[:3]==['nft','list','set']:
            out='set present\n'
        elif args[:4]==['nft','-j','list','set']:
            name=args[-1];values=self.grants if name=='wg_remote_peer_lan_v4' else self.lan_dest
            out=json.dumps({'nftables':[{'set':{'name':name,'elem':values}}]})
        else:raise AssertionError('Unexpected command: '+repr(args))
        return subprocess.CompletedProcess(args,code,out,'')

@pytest.fixture
def lab(tmp_path):
    system=FakeSystem();manager=mod.Manager(root=tmp_path,runner=system)
    conf=manager.config;conf.parent.mkdir(parents=True)
    conf.write_text('[Interface]\nPrivateKey = '+key(200)+'\nListenPort = 65312\nAddress = 10.255.246.1/24\nSaveConfig = true\n\n[Peer]\nPublicKey = '+key(1)+'\nAllowedIPs = 10.255.246.2/32\n')
    manager.legacy_profile.parent.mkdir(parents=True)
    manager.legacy_profile.write_text('[Interface]\nPrivateKey = '+key(2)+'\nAddress = 10.255.246.2/24\n\n[Peer]\nPublicKey = '+key(201)+'\nEndpoint = 198.51.100.10:65312\nAllowedIPs = 10.255.0.0/16\n')
    manager.policy_dir.mkdir(parents=True)
    (manager.policy_dir/'omr-admin-config.json').write_text(json.dumps({'users':[{'openmptcprouter':{'lanips':['192.168.100.0/24']}}]}))
    manager.gate_state.write_text('allow\n')
    manager.initialize(defer_firewall=True)
    def reconcile():
        if system.fail_policy:raise RuntimeError('simulated nft failure')
        data=mod.read_registry(manager.registry);configured=mod.parse_config(manager.config_text())
        system.grants,system.restricted=mod.policy_from_state(data,configured,system.live)
        system.lan_dest=['192.168.100.0/24'] if manager.gate_state.exists() else []
    manager.policy_apply=reconcile;manager.reconcile()
    return manager,system

def test_legacy_preserved_and_two_new_clients_denied_by_default(lab):
    m,s=lab
    first,profile=m.add('Alice');second,_=m.add('Bob')
    assert (first['ip'],second['ip'])==('10.255.246.3','10.255.246.4')
    assert s.live[key(1)]=='10.255.246.2'
    assert s.grants==['10.255.246.2']
    assert set(s.restricted)=={'10.255.246.3','10.255.246.4'}
    assert profile.stat().st_mode & 0o777==0o600
    assert m.clients.stat().st_mode & 0o777==0o700
    assert m.registry.stat().st_mode & 0o777==0o600
    assert m.state_dir.stat().st_mode & 0o777==0o700
    assert mod.parse_config(m.config_text())==s.live

def test_per_client_grant_global_gate_and_revoke(lab):
    m,s=lab;m.add('Alice');m.add('Bob')
    m.set_lan('Alice',True)
    assert s.grants==['10.255.246.2','10.255.246.3']
    state={p['name']:p for p in m.status()['peers']}
    assert state['Alice']['lan_firewall_open'] is True
    assert state['Bob']['lan_firewall_open'] is False
    assert state['Alice']['handshake_recent'] is True
    m.gate_state.unlink();m.reconcile()
    assert not {p['name']:p for p in m.status()['peers']}['Alice']['lan_firewall_open']
    assert not m.gate_state.exists(), 'per-peer action must not enable the master gate'
    m.gate_state.write_text('allow\n');m.reconcile();m.set_lan('Alice',False)
    assert '10.255.246.3' not in s.grants
    assert len(s.live)==3, 'revoking LAN must keep the WireGuard peers connected'


def test_status_reports_stale_open_nft_grant_instead_of_claiming_closed(lab):
    m,s=lab;m.add('Alice');m.set_lan('Alice',True)
    m.gate_state.unlink()  # simulate a state/firewall interruption before refresh
    row=next(p for p in m.status()['peers'] if p['name']=='Alice')
    assert not row['master_lan'] and row['lan_firewall_open'] and row['firewall_out_of_sync']
    m.reconcile()
    row=next(p for p in m.status()['peers'] if p['name']=='Alice')
    assert not row['lan_firewall_open'] and not row['firewall_out_of_sync']


def test_status_reports_unreadable_firewall_as_unknown(lab):
    m,s=lab
    def missing_nft(args,**kwargs):
        if args[:4]==['nft','-j','list','set']:
            return subprocess.CompletedProcess(args,1,'','')
        return s(args,**kwargs)
    m.runner=missing_nft
    row=m.status()['peers'][0]
    assert row['lan_firewall_open'] is None and row['firewall_out_of_sync'] is None

def test_disable_enable_and_remove_preserve_other_peers(lab):
    m,s=lab;m.add('Alice');m.add('Bob');m.set_lan('Alice',True)
    before=s.live.copy();m.disable('Alice')
    assert len(s.live)==2 and key(1) in s.live
    assert '10.255.246.3' not in s.grants
    m.enable('Alice');assert s.live==before
    assert '10.255.246.3' in s.grants
    m.disable('Alice',remove=True);assert len(s.live)==2
    assert not (m.clients/'Alice.conf').exists()
    m.add('Carol');assert mod.read_registry(m.registry)['peers'][-1]['ip']=='10.255.246.3'
    assert '10.255.246.3' not in s.grants, 'a new key must not inherit the prior grant'
    assert key(1) in s.live and m.legacy_profile.exists()

def test_failed_add_and_recovery_keep_ip_reserved_and_other_peer(lab):
    m,s=lab;m.add('Bob');s.fail_next_add=True
    with pytest.raises(mod.ManagerError):m.add('Alice')
    p=next(p for p in mod.read_registry(m.registry)['peers'] if p['name']=='Alice')
    assert p['state']=='adding' and p['ip'] not in s.grants
    assert key(1) in s.live and len(s.live)==2
    with pytest.raises(mod.ManagerError):m.add('Carol',ip=p['ip'])
    m.recover()
    assert next(p for p in mod.read_registry(m.registry)['peers'] if p['name']=='Alice')['state']=='disabled'
    assert p['ip'] not in s.grants and key(1) in s.live


def test_saveconfig_race_leaves_new_peer_pending_for_recovery(lab):
    m,s=lab
    def racing_runner(args,**kwargs):
        result=s(args,**kwargs)
        if args[:4]==['wg','set','client-wg0','peer'] and 'allowed-ips' in args:
            m.config.write_text(mod.remove_peer_block(m.config.read_text(),args[4]))
        return result
    m.runner=racing_runner
    with pytest.raises(mod.ManagerError,match='run recover'):
        m.add('Alice')
    peer=next(p for p in mod.read_registry(m.registry)['peers'] if p['name']=='Alice')
    assert peer['state']=='adding' and peer['public_key'] in s.live
    m.runner=s;m.recover()
    assert peer['public_key'] not in s.live and len(s.live)==1
    assert next(p for p in mod.read_registry(m.registry)['peers'] if p['name']=='Alice')['state']=='disabled'

def test_firewall_failure_on_lan_revoke_disables_the_affected_key(lab):
    m,s=lab;p,_=m.add('Alice');m.set_lan('Alice',True);s.fail_policy=True
    with pytest.raises(mod.ManagerError):m.set_lan('Alice',False)
    assert p['public_key'] not in s.live and key(1) in s.live
    saved=next(x for x in mod.read_registry(m.registry)['peers'] if x['name']=='Alice')
    assert saved['state']=='quarantine' and saved['lan'] is False
    assert saved['ip']=='10.255.246.3'


def test_firewall_failure_on_client_removal_disables_only_affected_key(lab):
    m,s=lab;p,_=m.add('Alice');m.add('Bob');m.set_lan('Alice',True);s.fail_policy=True
    with pytest.raises(mod.ManagerError, match='affected peer was disabled'):
        m.disable('Alice',remove=True)
    assert p['public_key'] not in s.live and len(s.live)==2
    saved=next(x for x in mod.read_registry(m.registry)['peers'] if x['name']=='Alice')
    assert saved['state']=='quarantine' and saved['ip']=='10.255.246.3'

def test_corrupt_or_missing_registry_and_runtime_drift_fail_closed(lab):
    m,s=lab
    m.registry.write_text('broken')
    assert mod.peer_policy(m.registry,m.config)==([],['10.255.246.0/24'])
    m.registry.unlink()
    with pytest.raises(mod.ManagerError):m.initialize(defer_firewall=True)
    data={'version':1,'peers':[{'name':'legacy_2','public_key':key(1),'ip':'10.255.246.2','legacy':True,'lan':True,'state':'active','mode':'split'}]}
    grants,restrict=mod.policy_from_state(data,{key(1):'10.255.246.2'},{key(9):'10.255.246.2'})
    assert grants==[] and restrict==['10.255.246.2']


def test_invalid_registry_field_types_are_rejected_without_traceback(lab):
    m,s=lab
    data=mod.read_registry(m.registry);data['peers'][0]['name']=123
    m.registry.write_text(json.dumps(data))
    with pytest.raises(mod.ManagerError):m.initialize(defer_firewall=True)
    assert mod.peer_policy(m.registry,m.config)==([],['10.255.246.0/24'])

@pytest.mark.parametrize('allowed',['10.255.246.0/24','10.255.246.2/32, 2001:db8::2/128','192.168.1.2/32'])
def test_unsafe_legacy_migration_is_rejected(tmp_path,allowed):
    m=mod.Manager(root=tmp_path,runner=FakeSystem());m.config.parent.mkdir(parents=True)
    m.config.write_text('[Interface]\nAddress = 10.255.246.1/24\n[Peer]\nPublicKey = '+key(1)+'\nAllowedIPs = '+allowed+'\n')
    original=m.config.read_bytes()
    with pytest.raises(mod.ManagerError):m.initialize(defer_firewall=True)
    assert m.config.read_bytes()==original and not m.marker.exists()

def test_split_export_includes_lan_only_after_explicit_permission(lab):
    m,s=lab;m.add('Alice');m.add('Bob',mode='full')
    assert 'AllowedIPs = 10.255.0.0/16\n' in m.profile('Alice')
    m.set_lan('Alice',True)
    assert 'AllowedIPs = 10.255.0.0/16,192.168.100.0/24\n' in m.profile('Alice')
    assert 'AllowedIPs = 0.0.0.0/0\n' in m.profile('Bob')
    assert m.profile('legacy_2')==m.legacy_profile.read_text()


@pytest.mark.parametrize('mutation',[
    lambda t:t.replace(key(2),key(3)),
    lambda t:t.replace(key(2),'malformed'),
    lambda t:t.replace('Address = 10.255.246.2/24','Address = 10.255.246.3/24'),
    lambda t:t.replace('Address = 10.255.246.2/24','Address = invalid'),
    lambda t:t.replace('PrivateKey = '+key(2),'PrivateKey = '+key(2)+'\nPrivateKey = '+key(2)),
])
def test_legacy_export_rejects_wrong_or_malformed_identity_without_disclosing_key(lab,mutation):
    m,s=lab;original=m.legacy_profile.read_text()
    m.legacy_profile.write_text(mutation(original))
    with pytest.raises(mod.ManagerError,match='Legacy profile unavailable') as error:
        m.profile('legacy_2')
    assert key(2) not in str(error.value) and key(3) not in str(error.value)


def test_split_lan_export_refuses_missing_or_overlapping_router_subnets(lab):
    m,s=lab;m.add('Alice');m.set_lan('Alice',True)
    config=m.policy_dir/'omr-admin-config.json'
    for lanips in ([],['10.255.246.0/24']):
        config.write_text(json.dumps({'users':[{'openmptcprouter':{'lanips':lanips}}]}))
        with pytest.raises(mod.ManagerError):m.profile('Alice')

def test_refuses_live_drift_or_unloaded_policy_before_add(lab):
    m,s=lab;s.live[key(9)]='10.255.246.22'
    with pytest.raises(mod.ManagerError):m.add('Alice')
    s.live.pop(key(9));old=s.__call__
    def runner(args,**kw):
        if args[:3]==['nft','list','set']:return subprocess.CompletedProcess(args,1,'','')
        return old(args,**kw)
    m.runner=runner
    with pytest.raises(mod.ManagerError):m.add('Alice')
    assert len(s.live)==1 and not (m.clients/'Alice.conf').exists()

def test_gateway_rules_check_peer_in_both_directions_and_input_precedes_established():
    rules=(ROOT/'nftables/omr.nft').read_text()
    assert 'ip saddr @wg_remote_peer_lan_v4 ip daddr @wg_remote_lan_v4 accept' in rules
    assert 'ip daddr @wg_remote_peer_lan_v4 ip saddr @wg_remote_lan_v4 accept' in rules
    chain=rules.split('chain input {',1)[1].split('chain forward {',1)[0]
    assert chain.index('ip saddr @wg_remote_peer_restrict_v4 reject') < chain.index('ct state established,related accept')


@pytest.mark.parametrize('element',[
    '10.255.246.3',
    {'prefix':{'addr':'10.255.246.2','len':31}},
    {'range':['10.255.246.2','10.255.246.4']},
    {'elem':{'val':{'range':['10.255.246.2','10.255.246.4']}}},
])
def test_status_parses_nft_interval_formats(element):
    assert mod.nft_set_contains([element],'10.255.246.3')
    assert not mod.nft_set_contains([element],'10.255.246.8')


@pytest.mark.parametrize('disk_rules',['set wg_remote_peer_lan_v4','old rules without peer sets',None])
def test_four_nft_sets_are_refreshed_in_one_fail_closed_transaction(tmp_path, monkeypatch,disk_rules):
    loader=importlib.machinery.SourceFileLoader('wg_gate_lab',str(ROOT/'wg-remote-lan-route'))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    gate=importlib.util.module_from_spec(spec);loader.exec_module(gate)
    gate.NFT_RULESET=tmp_path/'omr.nft'
    if disk_rules is not None:gate.NFT_RULESET.write_text(disk_rules)
    gate.PEER_REGISTRY=tmp_path/'missing.json';gate.WG_CONFIG=tmp_path/'missing.conf'
    calls=[]
    def nft_run(args,**kwargs):
        calls.append((args,kwargs))
        return subprocess.CompletedProcess(args,0,'','')
    monkeypatch.setattr(gate.subprocess,'run',nft_run)
    gate.sync_nft(mod.ipaddress.IPv4Address('10.255.220.2'), [mod.ipaddress.IPv4Network('192.168.100.0/24')])
    batches=[kwargs['input'] for args,kwargs in calls if args==['nft','-f','-']]
    assert len(batches)==1
    lines=batches[0].splitlines()
    assert sum(line.startswith('flush set ') for line in lines)==4
    assert 'add element inet omr wg_remote_peer_restrict_v4 { 10.255.246.0/24 }' in lines
    assert not any(line.startswith('add element inet omr wg_remote_peer_lan_v4') for line in lines)


@pytest.mark.parametrize('table_state',['unreadable','peer_set_present','malformed'])
def test_firewall_probe_failure_never_silently_downgrades_to_old_rules(tmp_path,monkeypatch,table_state):
    loader=importlib.machinery.SourceFileLoader('wg_gate_probe_failure',str(ROOT/'wg-remote-lan-route'))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    gate=importlib.util.module_from_spec(spec);loader.exec_module(gate)
    gate.NFT_RULESET=tmp_path/'old.nft';gate.NFT_RULESET.write_text('old rules')
    calls=[]
    def nft_run(args,**kwargs):
        calls.append(args)
        if args[:3]==['nft','list','set']:
            return subprocess.CompletedProcess(args,1,'','')
        if args[:4]==['nft','-j','list','table']:
            if table_state=='unreadable':raise subprocess.CalledProcessError(1,args)
            doc={'nftables':[{'table':{'family':'inet','name':'omr'}}]}
            if table_state=='peer_set_present':doc['nftables'].append({'set':{'name':'wg_remote_peer_lan_v4'}})
            return subprocess.CompletedProcess(args,0,'bad json' if table_state=='malformed' else json.dumps(doc),'')
        raise AssertionError('Unexpected nft mutation')
    monkeypatch.setattr(gate.subprocess,'run',nft_run)
    with pytest.raises((subprocess.CalledProcessError,ValueError)):
        gate.sync_nft(None,[])
    assert ['nft','-f','-'] not in calls


@pytest.mark.parametrize('firewall_fails',[False,True])
def test_missing_rules_file_revokes_live_firewall_or_returns_failure(tmp_path,monkeypatch,firewall_fails):
    loader=importlib.machinery.SourceFileLoader('wg_gate_missing',str(ROOT/'wg-remote-lan-route'))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    gate=importlib.util.module_from_spec(spec);loader.exec_module(gate)
    gate.NFT_RULESET=tmp_path/'absent.nft';gate.STATE=tmp_path/'allow';gate.STATE.write_text('allow\n')
    gate.LOCK=tmp_path/'lock';gate.CONFIG=tmp_path/'absent-config.json'
    calls=[]
    def sync(remote,networks):
        calls.append(('nft',remote,networks))
        if firewall_fails:
            raise subprocess.CalledProcessError(1,['nft'])
    monkeypatch.setattr(gate,'sync_nft',sync)
    monkeypatch.setattr(gate,'clear_policy_routes',lambda:calls.append(('clear',)))
    monkeypatch.setattr(gate.sys,'argv',['wg-remote-lan-route','--config',str(gate.CONFIG),'--lan-access','deny'])
    if firewall_fails:
        with pytest.raises(subprocess.CalledProcessError):gate.main()
    else:
        assert gate.main()==0
    assert calls[0]==('nft',None,[]) and ('clear',) in calls
    assert not gate.STATE.exists()


@pytest.mark.parametrize('interface_up',[True,False])
def test_staged_snapshot_preserves_fresh_or_existing_legacy_peer_before_firewall(tmp_path,interface_up):
    system=FakeSystem()
    def runner(args,**kwargs):
        if not interface_up and args==['wg','show','client-wg0','allowed-ips']:
            return subprocess.CompletedProcess(args,1,'','')
        return system(args,**kwargs)
    applied=[];m=mod.Manager(root=tmp_path,runner=runner,policy_apply=lambda:applied.append(True))
    m.config.parent.mkdir(parents=True)
    original='[Interface]\nAddress = 10.255.246.1/24\n[Peer]\nPublicKey = '+key(1)+'\nAllowedIPs = 10.255.246.2/32\n'
    m.config.write_text(original)
    legacy_live=system.live.copy()
    data=m.initialize(defer_firewall=True)
    assert m.config.read_text()==original and system.live==legacy_live and applied==[]
    assert data['peers'][0]['legacy'] and data['peers'][0]['public_key']==key(1)
    assert data['peers'][0]['ip']=='10.255.246.2' and data['peers'][0]['lan']


def test_frozen_installer_stages_manager_and_snapshot_before_helper_and_firewall():
    script=(ROOT/'debian9-x86_64.sh').read_text()
    start=script.index('if [ "$WIREGUARD" = "yes" ]; then')
    block=script[start:]
    fresh=block.index('if [ ! -f /etc/wireguard/client-wg0.conf ]; then')
    wrap=block.index('install -m 0755 "$DIR/omr-wg-manager"')
    backend=block.index('install -m 0644 "$DIR/omr_wg_manager.py"')
    snapshot=block.index('/usr/local/sbin/omr-wg-manager init --defer-firewall')
    helper=block.index('install -m 0755 "$DIR/wg-remote-lan-route"')
    firewall=block.index('cp ${DIR}/nftables/omr.nft /etc/nftables/omr.nft')
    reload=block.index('systemctl -q restart nftables')
    assert fresh < wrap < snapshot < helper < firewall < reload
    assert wrap < backend < snapshot
    for required in ('omr-wg-manager','omr_wg_manager.py','wg-remote-lan-route'):
        assert (ROOT/required).is_file()
