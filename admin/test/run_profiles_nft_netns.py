#!/usr/bin/env python3
"""Packet lab for VPS profile route changes; all keys and namespaces ephemeral."""
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'admin'))
sys.path.insert(0, str(REPO))
import omr_profiles as profiles
spec = importlib.util.spec_from_file_location('wg_lab', REPO / 'tests/run_omr_wg_netns.py')
wg = importlib.util.module_from_spec(spec); spec.loader.exec_module(wg)

SERVER = r'''import socket,sys,threading
s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
s.bind(('0.0.0.0',int(sys.argv[1])));s.listen(16)
def handle(c):
 with c:
  try:
   while True:
    data=c.recv(1024)
    if not data:return
    c.sendall(data if sys.argv[2]=='echo' else sys.argv[2].encode())
  except OSError:return
while True:
 c,_=s.accept();threading.Thread(target=handle,args=(c,),daemon=True).start()
'''


def inner(root, names):
    events={}
    def check(name,condition):
        if not condition:raise AssertionError(name)
        events[name]=True
    runtime=profiles.Runtime(lambda _: {},lambda _:None,lambda:None,
        mq_config=str(root/'mq.json'),admin_config=str(root/'admin.json'),
        vpn_file=str(root/'current-vpn'),proxy_file=str(root/'current-proxy'),
        glory_config=str(root/'glory'),config_lock=str(root/'config.lock'),
        wg_helper=str(root/'wg-helper'))
    before=runtime._selection_snapshot()
    runtime._refresh_forwarding()
    saved_chains={name:wg.run(['nft','list','chain','inet','omr',name],capture=True)
                  for name in ('rpf_dnat_bypass','custom_dnat_bypass','dscp_mark')}
    check('original MQ tunnel GUI reachable through WireGuard',wg.probe(names['wg'],'10.255.220.2',80))
    check('original public forward targets MQ tunnel',wg.probe(names['public'],'198.51.100.1',8080,expected='mq'))
    runtime._set_selection('glorytun_tcp','none')
    runtime.apply_route('glorytun_tcp','10.255.255.2')
    check('Glorytun GUI target reachable through real WireGuard',wg.probe(names['wg'],'10.255.255.2',80))
    check('previous GUI address no longer implicitly allowed',not wg.probe(names['wg'],'10.255.220.2',80))
    check('public forwarding targets Glorytun endpoint',wg.probe(names['public'],'198.51.100.1',8080,expected='gt'))
    check('firewall bypass and DSCP chains remain untouched',all(
        wg.run(['nft','list','chain','inet','omr',name],capture=True)==rules for name,rules in saved_chains.items()))
    # Keep the master LAN opt-in enabled to demonstrate that removing the
    # target closes both GUI and LAN without changing the persistent gate.
    (root/'wg.allow').write_text('allow\n')
    runtime._refresh_forwarding()
    check('opted-in WG client reaches Glorytun LAN before no-tunnel',wg.probe(names['wg'],'192.168.100.5',8082))
    check('independent public reverse-proxy listener works before no-tunnel',wg.probe(names['public'],'198.51.100.1',9001,expected='rpf'))
    before_none=runtime._selection_snapshot()
    runtime._set_selection('none','shadowsocks-rust')
    runtime.apply_route('none',None)
    selected=json.loads((root/'admin.json').read_text())['users'][0]['openmptcprouter']
    check('no-tunnel clears only the primary tunnel target',selected.get('vpn')=='none' and 'vpnremoteip' not in selected)
    check('no-tunnel denies previous remote GUI and LAN',
          not wg.probe(names['wg'],'10.255.255.2',80) and not wg.probe(names['wg'],'192.168.100.5',8082))
    check('no-tunnel does not forward public VPN port to stale router',not wg.probe(names['public'],'198.51.100.1',8080,expected='gt'))
    check('no-tunnel retains independent reverse proxy and WG Internet',
          wg.probe(names['public'],'198.51.100.1',9001,expected='rpf') and wg.probe(names['wg'],'1.1.1.1',8085))
    check('no-tunnel preserves master LAN opt-in state and bypass chains',
          (root/'wg.allow').read_text()=='allow\n' and all(
            wg.run(['nft','list','chain','inet','omr',name],capture=True)==rules for name,rules in saved_chains.items()))
    runtime._set_selection(restore=before_none);runtime._refresh_forwarding()
    check('no-tunnel rollback restores opted-in GUI, LAN and public forward',
          wg.probe(names['wg'],'10.255.255.2',80) and wg.probe(names['wg'],'192.168.100.5',8082) and
          wg.probe(names['public'],'198.51.100.1',8080,expected='gt'))
    (root/'wg.allow').unlink()
    runtime._set_selection(restore=before);runtime._refresh_forwarding()
    check('rollback restores original MQ GUI target',wg.probe(names['wg'],'10.255.220.2',80))
    check('rollback restores original public forwarding target',wg.probe(names['public'],'198.51.100.1',8080,expected='mq'))
    check('rollback removes obsolete Glorytun GUI access',not wg.probe(names['wg'],'10.255.255.2',80))
    print(json.dumps({'passed':len(events),'checks':events,
        'scope':'real WireGuard and nft packet paths; MQVPN/Glorytun endpoints simulated with veth pairs; no production host or real tunnel handshake'},sort_keys=True))


def outer():
    if os.geteuid():raise RuntimeError('requires root with ip, nft and wg')
    token=secrets.token_hex(3)
    names={role:'omrpf'+token+suffix for role,suffix in [('server','s'),('mq','m'),('gt','g'),('public','p'),('wg','w')]}
    created=[];processes=[];host_links=[]
    with tempfile.TemporaryDirectory(prefix='omr-profile-netns-') as tmp:
        root=Path(tmp)
        try:
            for name in names.values():
                wg.run(['ip','netns','add',name]);created.append(name)
                wg.ns(name,'ip','link','set','lo','up')
            def pair(left,right,ldev,rdev,index):
                a,b='p'+token+str(index)+'a','p'+token+str(index)+'b'
                host_links.extend((a,b));wg.run(['ip','link','add',a,'type','veth','peer','name',b])
                wg.run(['ip','link','set',a,'netns',names[left]])
                wg.run(['ip','link','set',b,'netns',names[right]])
                for role,old,new in ((left,a,ldev),(right,b,rdev)):
                    wg.ns(names[role],'ip','link','set',old,'name',new)
                    wg.ns(names[role],'ip','link','set',new,'up')
            s,m,g,p,w=(names[x] for x in ('server','mq','gt','public','wg'))
            pair('server','mq','mqvpn0','router0',1)
            wg.ns(s,'ip','addr','add','10.255.220.1/24','dev','mqvpn0')
            wg.ns(m,'ip','addr','add','10.255.220.2/24','dev','router0')
            pair('server','gt','gt-tun0','router0',2)
            wg.ns(s,'ip','addr','add','10.255.255.1/30','dev','gt-tun0')
            wg.ns(g,'ip','addr','add','10.255.255.2/30','dev','router0')
            wg.ns(g,'ip','addr','add','192.168.100.5/32','dev','lo')
            wg.ns(s,'ip','route','add','192.168.100.0/24','via','10.255.255.2','dev','gt-tun0')
            pair('server','public','wan0','outside0',3)
            wg.ns(s,'ip','addr','add','198.51.100.1/24','dev','wan0')
            wg.ns(p,'ip','addr','add','198.51.100.2/24','dev','outside0')
            wg.ns(p,'ip','addr','add','1.1.1.1/32','dev','lo')
            wg.ns(s,'ip','route','add','1.1.1.1/32','via','198.51.100.2','dev','wan0')
            wg.ns(m,'ip','route','add','198.51.100.0/24','via','10.255.220.1')
            wg.ns(g,'ip','route','add','198.51.100.0/24','via','10.255.255.1')
            pair('server','wg','underlay0','outside0',4)
            wg.ns(s,'ip','addr','add','172.24.0.1/24','dev','underlay0')
            wg.ns(w,'ip','addr','add','172.24.0.2/24','dev','outside0')
            wg.ns(s,'sysctl','-q','-w','net.ipv4.ip_forward=1')
            secret,server_pub=wg.keypair();client_secret,client_pub=wg.keypair()
            wg.private_file(root/'server.key',secret)
            wg.ns(s,'ip','link','add','client-wg0','type','wireguard')
            wg.ns(s,'wg','set','client-wg0','private-key',str(root/'server.key'),
                  'listen-port','65312','peer',client_pub,'allowed-ips','10.255.246.2/32')
            wg.ns(s,'ip','addr','add','10.255.246.1/24','dev','client-wg0')
            wg.ns(s,'ip','link','set','client-wg0','up')
            wg.configure_client(w,client_secret,'10.255.246.2',server_pub,root)
            (root/'wg.conf').write_text('[Interface]\nAddress = 10.255.246.1/24\nPrivateKey = '+secret+
                '\n[Peer]\nPublicKey = '+client_pub+'\nAllowedIPs = 10.255.246.2/32\n')
            (root/'peers.json').write_text(json.dumps({'version':1,'peers':[{'name':'legacy_2',
                'public_key':client_pub,'ip':'10.255.246.2','legacy':True,'lan':True,'state':'active','mode':'split'}]}))
            (root/'admin.json').write_text(json.dumps({'users':[{'openmptcprouter':{'userid':0,
                'vpn':'mqvpn','proxy':'shadowsocks-rust','vpnremoteip':'10.255.220.2',
                'lanips':['192.168.100.0/24'],
                'fw_ports':[{'name':'web','port':'8080','proto':'tcp','fwtype':'DNAT','family':4,'vpn':'default'},
                            {'name':'reverse-proxy','port':'9001','proto':'tcp','fwtype':'ACCEPT','family':4}]}}]}))
            (root/'mq.json').write_text(json.dumps({'subnet':'10.255.220.0/24',
                'users':[{'name':'openmptcprouter','fixed_ip':'10.255.220.2'}]}))
            (root/'glory').write_text('MPTCP=true\n')
            (root/'current-vpn').write_text('mqvpn\n');(root/'current-proxy').write_text('shadowsocks-rust\n')
            variables=(REPO/'nftables/omr-vars.nft').read_text().replace('define NET_IFACE = eth0','define NET_IFACE = wan0')
            original=(REPO/'nftables/omr.nft').read_text()
            (root/'omr.nft').write_text(original);(root/'rules.nft').write_text(variables+'\n'+original)
            wg.ns(s,'nft','-f',str(root/'rules.nft'))
            for chain,port in (('rpf_dnat_bypass','9001'),('custom_dnat_bypass','9002')):
                wg.ns(s,'nft','add','rule','inet','omr',chain,'tcp','dport',port,'accept')
            wg.ns(s,'nft','add','rule','inet','omr','dscp_mark','meta','nfproto','ipv6','return')
            helper='''#!/usr/bin/python3\nimport importlib.machinery,importlib.util,sys\nfrom pathlib import Path\nsys.path.insert(0,{repo!r})\nloader=importlib.machinery.SourceFileLoader('gate',{helper!r})\nspec=importlib.util.spec_from_loader(loader.name,loader);g=importlib.util.module_from_spec(spec);loader.exec_module(g)\ng.CONFIG=Path({config!r});g.STATE=Path({state!r});g.LOCK=Path({lock!r});g.NFT_RULESET=Path({rules!r})\ng.MQVPN_CONFIG=Path({missing!r});g.PEER_REGISTRY=Path({registry!r});g.WG_CONFIG=Path({wgconf!r})\nsys.argv=['wg-remote-lan-route'];raise SystemExit(g.main())\n'''.format(
                repo=str(REPO),helper=str(REPO/'wg-remote-lan-route'),config=str(root/'admin.json'),
                state=str(root/'wg.allow'),lock=str(root/'wg.lock'),rules=str(root/'omr.nft'),
                missing=str(root/'absent.json'),registry=str(root/'peers.json'),wgconf=str(root/'wg.conf'))
            (root/'wg-helper').write_text(helper);(root/'wg-helper').chmod(0o700)
            for nsname,label in ((m,'mq'),(g,'gt')):
                for port,mode in ((80,'echo'),(8080,label)):
                    processes.append(subprocess.Popen(['ip','netns','exec',nsname,'python3','-u','-c',SERVER,str(port),mode],
                        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
            for nsname,port,mode in ((g,8082,'echo'),(p,8085,'echo'),(s,9001,'rpf')):
                processes.append(subprocess.Popen(['ip','netns','exec',nsname,'python3','-u','-c',SERVER,str(port),mode],
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
            time.sleep(.4)
            if any(proc.poll() is not None for proc in processes):raise RuntimeError('test listener failed')
            result=subprocess.run(['ip','netns','exec',s,sys.executable,str(Path(__file__).resolve()),
                                   '--inner',str(root),json.dumps(names)],capture_output=True,text=True,timeout=70)
            if result.returncode:raise RuntimeError(result.stderr.strip() or 'packet lab failed')
            print(result.stdout.strip())
        finally:
            for proc in processes:proc.terminate()
            for proc in processes:
                try:proc.wait(timeout=2)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
            for name in reversed(created):wg.run(['ip','netns','del',name],check=False)
            for link in host_links:wg.run(['ip','link','del',link],check=False)


if __name__=='__main__':
    try:
        if len(sys.argv)==4 and sys.argv[1]=='--inner':inner(Path(sys.argv[2]),json.loads(sys.argv[3]))
        else:outer()
    except Exception as error:
        print(json.dumps({'result':'FAIL','reason':str(error)}),file=sys.stderr);sys.exit(1)
