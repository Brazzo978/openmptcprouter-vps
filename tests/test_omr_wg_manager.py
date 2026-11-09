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
    wrap=block.index('install -m 0755 "$DIR/omr-rth"')
    backend=block.index('install -m 0644 "$DIR/omr_wg_manager.py"')
    snapshot=block.index('/usr/local/sbin/omr-rth init --defer-firewall')
    helper=block.index('install -m 0755 "$DIR/wg-remote-lan-route"')
    firewall=block.index('cp ${DIR}/nftables/omr.nft /etc/nftables/omr.nft')
    reload=block.index('systemctl -q restart nftables')
    assert fresh < wrap < snapshot < helper < firewall < reload
    assert wrap < backend < snapshot
    assert 'install wireguard-tools qrencode --no-install-recommends' in block
    for required in ('omr-rth','omr-wg-manager','omr_wg_manager.py','wg-remote-lan-route'):
        assert (ROOT/required).is_file()


def test_installation_default_is_first_without_renaming_or_recreating_keys(lab):
    m,s=lab
    m.add('Alice'); m.add('Bob')
    data=mod.read_registry(m.registry)
    data['peers'].append(data['peers'].pop(0)); m.persist(data)
    keys_before=s.live.copy(); profile_before=m.legacy_profile.read_bytes(); s.calls.clear()
    rows=m.status()['peers']
    assert [p['name'] for p in rows]==['legacy_2','Alice','Bob']
    assert [p['installation_default'] for p in rows]==[True,False,False]
    assert s.live==keys_before and m.legacy_profile.read_bytes()==profile_before
    assert ['wg','genkey'] not in s.calls


def test_default_identity_uses_installer_public_key_and_does_not_guess_address(lab):
    m,s=lab; m.add('Alice')
    public=m.config.parent/'vpn-client-public.key'; public.write_text(key(99)+'\n')
    assert not any(p['installation_default'] for p in m.status()['peers'])
    public.write_text(key(1)+'\n')
    assert m.status()['peers'][0]['installation_default']
    public.unlink(); m.legacy_profile.write_text(m.legacy_profile.read_text().replace(key(2),key(9)))
    assert not any(p['installation_default'] for p in m.status()['peers'])


def test_reused_default_address_does_not_become_installation_default(lab):
    m,s=lab; m.disable('legacy_2',remove=True); m.add('Alice')
    row=m.status()['peers'][0]
    assert row['ip']=='10.255.246.2' and not row['installation_default']
    assert m.profile('Alice')!=m.legacy_profile.read_text()


def test_numbered_selection_retries_invalid_input_and_selects_default(lab,monkeypatch,capsys):
    m,s=lab; m.add('Alice')
    values=iter(['0','3','bad','1'])
    monkeypatch.setattr('builtins.input',lambda prompt:next(values))
    assert mod.select_client(m,'Select the existing client you want to revoke')=='legacy_2'
    output=capsys.readouterr().out
    assert '1) legacy_2 (installation default)' in output
    assert '2) Alice' in output and output.count('Choose one of the listed clients.')==3


def test_add_wizard_reuses_endpoint_and_allocates_after_installer_client(lab,monkeypatch,capsys):
    m,s=lab
    values=iter(['bad name','a_name_is_far_too_long','Alice','','bad','y'])
    monkeypatch.setattr('builtins.input',lambda prompt:next(values))
    monkeypatch.setattr(mod.shutil,'which',lambda command:None)
    original=m.legacy_profile.read_bytes()
    mod.new_client_wizard(m)
    peer=mod.read_registry(m.registry)['peers'][-1]
    assert peer['name']=='Alice' and peer['ip']=='10.255.246.3' and peer['mode']=='full'
    assert not peer['lan'] and m.legacy_profile.read_bytes()==original
    assert 'AllowedIPs = 0.0.0.0/0' in m.profile('Alice')
    assert 'Your client config file is in' in capsys.readouterr().out


def test_endpoint_inheritance_is_section_aware_and_accepts_wireguard_comments(lab):
    m,_=lab
    m.legacy_profile.write_text('[Interface]\nEndpoint = wrong.example:1234\n\n[Peer] # server\n'
                                'Endpoint = vps.example.net:65312 # retained server\n')
    assert m.endpoint()=='vps.example.net:65312'


@pytest.mark.parametrize('profile',[
    '[Interface]\nEndpoint = wrong.example:1234\n',
    '[Peer]\nEndpoint = one.example:1234\nEndpoint = two.example:1234\n',
    '[Peer]\nEndpoint = one.example:1234\n[Peer]\nEndpoint = two.example:1234\n',
])
def test_ambiguous_installer_endpoint_requires_explicit_override(lab,profile):
    m,_=lab; m.legacy_profile.write_text(profile)
    with pytest.raises(mod.ManagerError,match='missing or ambiguous'):
        m.endpoint()
    assert m.endpoint('override.example:65312')=='override.example:65312'


@pytest.mark.parametrize('endpoint',['vps.example.net:0','vps.example.net:65536',
                                     '[bad::123::456]:65312',
                                     '999.1.2.3:65312','bad..example:65312','-bad.example:65312','bad.example..:65312',
                                     'vps.example.net:65312\nDNS = 9.9.9.9'])
def test_explicit_endpoint_rejects_invalid_port_or_config_injection(lab,endpoint):
    m,_=lab
    with pytest.raises(mod.ManagerError):m.endpoint(endpoint)


def test_existing_ipv6_outer_endpoint_remains_compatible_without_ipv6_tunnel(lab):
    m,_=lab
    assert m.endpoint('[2001:db8::1]:65312')=='[2001:db8::1]:65312'


@pytest.mark.parametrize('fields,expected',[
    ('DNS = 9.9.9.9, 1.0.0.1 # existing resolvers\n','9.9.9.9, 1.0.0.1'),
    ('DNS = 9.9.9.9\nDNS = 9.9.9.9, 1.0.0.1\n','9.9.9.9, 1.0.0.1'),
    ('DNS = 999.1.2.3, bad.example, 8.8.8.8\n','8.8.8.8'),
    ('DNS = 2606:4700:4700::1111, local.example\n','1.1.1.1'),
    ('DNS = not-a-resolver;bad\n','1.1.1.1'),
    ('','1.1.1.1'),
])
def test_dns_inherits_valid_ipv4_only_and_deduplicates_directives(lab,fields,expected):
    m,_=lab
    m.legacy_profile.write_text('[Interface]\n'+fields+'[Peer]\nDNS = 6.6.6.6\n')
    before=m.legacy_profile.read_bytes()
    assert m.client_dns()==expected
    assert m.legacy_profile.read_bytes()==before


def test_new_profile_reuses_dns_without_changing_original_profile_or_default_key(lab):
    m,s=lab
    text=m.legacy_profile.read_text().replace('[Interface]\n','[Interface]\nDNS = 9.9.9.9, 1.0.0.1 # customized\n',1)
    m.legacy_profile.write_text(text); before=m.legacy_profile.read_bytes(); original_key=s.live.copy()
    m.add('Alice')
    assert 'DNS = 9.9.9.9, 1.0.0.1\n' in m.profile('Alice')
    assert m.legacy_profile.read_bytes()==before
    assert all(s.live.get(public)==address for public,address in original_key.items())


def test_new_profile_defaults_to_mtu_1320_and_keepalive_25(lab):
    m,_=lab; before=m.legacy_profile.read_bytes()
    m.add('Alice'); profile=m.profile('Alice')
    assert 'MTU = 1320\n' in profile and 'PersistentKeepalive = 25\n' in profile
    assert m.legacy_profile.read_bytes()==before


@pytest.mark.parametrize('mtu,keepalive',[('1380','15'),('1280','0'),('1400','off')])
def test_new_profile_inherits_explicit_mtu_and_keepalive_including_disabled(lab,mtu,keepalive):
    m,s=lab
    text=m.legacy_profile.read_text().replace('[Interface]\n','[Interface]\nMTU = '+mtu+' # chosen\n',1)
    text=text.replace('[Peer]\n','[Peer]\nPersistentKeepalive = '+keepalive+' # chosen\n',1)
    m.legacy_profile.write_text(text); original=m.legacy_profile.read_bytes(); legacy=s.live.copy()
    m.add('Alice'); generated=m.profile('Alice')
    assert 'MTU = '+mtu+'\n' in generated and 'PersistentKeepalive = '+keepalive+'\n' in generated
    assert m.legacy_profile.read_bytes()==original
    assert all(s.live.get(key)==address for key,address in legacy.items())


def test_link_settings_ignore_fields_in_wrong_sections(lab):
    m,_=lab
    m.legacy_profile.write_text('[Interface]\nPersistentKeepalive = 7\n[Peer]\nMTU = 1500\n')
    assert m.client_link_settings()==('1320','25')


@pytest.mark.parametrize('text',[
    '[Interface]\nMTU = 1320\nMTU = 1400\n',
    '[Interface]\nMTU = 1320\n[Interface]\nMTU = 1400\n',
    '[Interface]\nMTU = 0\n', '[Interface]\nMTU = auto\n',
    '[Interface]\nMTU = 65536\n',
    '[Peer]\nPersistentKeepalive = 25\nPersistentKeepalive = 15\n',
    '[Peer]\nPersistentKeepalive = -1\n', '[Peer]\nPersistentKeepalive = 65536\n',
    '[Peer]\nPersistentKeepalive = yes\n',
])
def test_malformed_or_duplicate_explicit_link_settings_are_rejected(lab,text):
    m,_=lab; m.legacy_profile.write_text(text); before=m.legacy_profile.read_bytes()
    with pytest.raises(mod.ManagerError):m.client_link_settings()
    assert m.legacy_profile.read_bytes()==before


def test_installer_mtu_flag_only_adds_missing_server_mtu_without_live_changes(lab):
    m,s=lab; before=m.config.read_text(); original_profile=m.legacy_profile.read_bytes()
    router_config=m.config.parent/'wg0.conf'; router_config.write_text('router-owned original\n')
    s.calls.clear(); m.initialize(defer_firewall=True,default_server_mtu=True)
    assert m.config.read_text()==before.replace('[Interface]\n','[Interface]\nMTU = 1320\n',1)
    assert m.legacy_profile.read_bytes()==original_profile
    assert router_config.read_text()=='router-owned original\n'
    assert not s.calls


def test_server_mtu_existing_explicit_value_is_preserved_and_regular_init_leaves_absent_mtu(lab):
    m,_=lab; original=m.config.read_bytes()
    m.initialize(); assert m.config.read_bytes()==original
    m.config.write_text(m.config.read_text().replace('[Interface]\n','[Interface]\nMTU = 1420 # explicit\n',1))
    explicit=m.config.read_bytes(); m.initialize(defer_firewall=True,default_server_mtu=True)
    assert m.config.read_bytes()==explicit


def test_mtu_flag_does_not_change_config_when_registry_is_lost(lab):
    m,_=lab; original=m.config.read_bytes(); m.registry.unlink()
    with pytest.raises(mod.ManagerError):m.initialize(default_server_mtu=True)
    assert m.config.read_bytes()==original


def test_fresh_installer_defaults_only_rth_server_and_installation_client():
    script=(ROOT/'debian9-x86_64.sh').read_text()
    router=script.split('cat > /etc/wireguard/wg0.conf <<-EOF',1)[1].split('\n\t\tEOF',1)[0]
    server=script.split('cat > /etc/wireguard/client-wg0.conf <<-EOF',1)[1].split('\n\t\tEOF',1)[0]
    client=script.split('cat > /root/wireguard-client.conf <<-EOF',1)[1].split('\n\t\tEOF',1)[0]
    assert 'MTU = 1320' not in router
    assert 'MTU = 1320' in server and 'MTU = 1320' in client
    assert 'PersistentKeepalive = 25' in client
    assert script.count('omr-rth init --defer-firewall --default-server-mtu')==2


def test_add_wizard_retries_duplicate_name_and_invalid_or_reserved_address(lab,monkeypatch):
    m,_=lab; m.add('Alice')
    values=iter(['alice','Bob','2','255','192.168.1.5','4','n'])
    monkeypatch.setattr('builtins.input',lambda prompt:next(values))
    monkeypatch.setattr(mod.shutil,'which',lambda command:None)
    mod.new_client_wizard(m)
    peer=mod.read_registry(m.registry)['peers'][-1]
    assert peer['name']=='Bob' and peer['ip']=='10.255.246.4' and peer['mode']=='split'


def test_add_wizard_reports_saved_profile_even_if_qr_rendering_fails(lab,monkeypatch,capsys):
    m,_=lab; values=iter(['Alice','','n'])
    monkeypatch.setattr('builtins.input',lambda prompt:next(values))
    monkeypatch.setattr(mod.shutil,'which',lambda command:'/usr/bin/qrencode')
    def failed_qr(*args):raise mod.ManagerError('Synthetic QR failure')
    monkeypatch.setattr(mod,'show_qr',failed_qr)
    mod.new_client_wizard(m)
    output=capsys.readouterr()
    assert 'Your client config file is in' in output.out
    assert 'Client created; QR display failed.' in output.err
    assert (m.clients/'Alice.conf').exists()


def test_no_endpoint_value_is_displayed_as_not_set(lab,capsys):
    m,s=lab
    def fields(args,**kwargs):
        if args==['wg','show','client-wg0','endpoints']:
            return subprocess.CompletedProcess(args,0,key(1)+'\t(none)\n','')
        return s(args,**kwargs)
    m.runner=fields
    mod.display_connected_clients(m.status())
    output=capsys.readouterr().out
    assert 'Not set' in output and '(none)' not in output


def test_menu_revoke_requires_confirmation_and_handles_errors(lab,monkeypatch,capsys):
    m,s=lab; m.add('Alice')
    values=iter(['99','3','1','n','7','2','8','2','12'])
    monkeypatch.setattr('builtins.input',lambda prompt:next(values))
    assert mod.interactive_menu(m)==0
    assert key(1) in s.live and len(s.live)==2
    output=capsys.readouterr().out
    assert 'Choose one of the listed options.' in output
    assert 'Client disabled.' in output and 'Client enabled.' in output
    assert 'IPv6' not in output and 'Port Forwarding' not in output


def test_menu_revoke_selected_additional_peer_preserves_default(lab,monkeypatch):
    m,s=lab; m.add('Alice')
    values=iter(['3','2','y','12'])
    monkeypatch.setattr('builtins.input',lambda prompt:next(values))
    assert mod.interactive_menu(m)==0
    assert s.live=={key(1):'10.255.246.2'}
    assert m.legacy_profile.exists()


def test_menu_eof_and_empty_selection_are_safe(lab,monkeypatch,capsys):
    m,s=lab
    def eof(prompt):raise EOFError
    monkeypatch.setattr('builtins.input',eof)
    assert mod.interactive_menu(m)==0
    m.disable('legacy_2',remove=True)
    assert mod.select_client(m,'Select a client') is None
    assert 'You have no existing clients!' in capsys.readouterr().out


def test_reference_connected_display_parses_targeted_public_wireguard_fields(lab,capsys):
    m,s=lab
    def fields(args,**kwargs):
        if args==['wg','show','client-wg0','endpoints']:
            return subprocess.CompletedProcess(args,0,key(1)+'\t198.51.100.11:52222\n','')
        return s(args,**kwargs)
    m.runner=fields
    info=m.status(); row=info['peers'][0]
    row.update(last_handshake_age_seconds=10,rx_bytes=1048576,tx_bytes=1048576)
    mod.display_connected_clients(info,now=1735689600)
    output=capsys.readouterr().out
    assert '| Client IP          | Last Handshake    | Status' in output
    assert '2024/12/31 23:59' in output and 'Connected' in output
    assert '198.51.100.11:52222' in output and '2 MB' in output
    assert key(1) not in output and key(2) not in output
    assert ['wg','show','all','dump'] not in s.calls


@pytest.mark.parametrize('age,expected',[(None,'Never Connected'),(239,'Connected'),(240,'Disconnected')])
def test_connected_display_matches_reference_four_minute_threshold(lab,capsys,age,expected):
    m,_=lab; info=m.status(); info['peers'][0]['last_handshake_age_seconds']=age
    mod.display_connected_clients(info,now=1735689600)
    output=capsys.readouterr().out
    assert expected in output
    if age is None:assert 'Never' in output and 'Not set' in output


def test_remote_installer_also_installs_canonical_command_and_initializes_before_helper():
    script=(ROOT/'debian9-x86_64.sh').read_text()
    start=script.index('for wg_file in omr-rth omr-wg-manager omr_wg_manager.py; do')
    block=script[start:]
    assert block.index('/usr/local/sbin/omr-rth init --defer-firewall') < block.index('wget -O /usr/local/sbin/wg-remote-lan-route')
    assert 'exec /usr/local/sbin/omr-rth "$@"' in (ROOT/'omr-wg-manager').read_text()
    assert 'exec python3 "$helper" menu' in (ROOT/'omr-rth').read_text()
