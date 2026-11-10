"""Actual nft/UDP/TCP regression lab; all links and rules belong to QA namespaces."""
from pathlib import Path
import importlib.util,json,os,subprocess,sys,tempfile,time,uuid
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('render',ROOT.parent/'admin/omr_profile_firewall.py');render=importlib.util.module_from_spec(spec);spec.loader.exec_module(render)
tag=uuid.uuid4().hex[:6];names={k:'dnat'+tag+k for k in ['r','s','e']};created=[];processes=[];checks={}
def run(args,**kw):return subprocess.run(args,capture_output=True,text=True,check=True,timeout=8,**kw).stdout.strip()
def ns(which,*args,**kw):return run(['ip','netns','exec',names[which],*args],**kw)
def record(name,ok):
 checks[name]=bool(ok)
 if not ok:raise AssertionError(name)
server=r'''
import socket,sys,threading
marker=sys.argv[1].encode()
def udp():
 s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind((sys.argv[2],53))
 while True:
  data,peer=s.recvfrom(4096);s.sendto(marker,peer)
threading.Thread(target=udp,daemon=True).start()
s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('0.0.0.0',18080));s.listen()
while True:
 c,_=s.accept();c.recv(100);c.sendall(marker);c.close()
'''
client=r'''
import socket,sys
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM if sys.argv[1]=='udp' else socket.SOCK_STREAM);s.settimeout(.8)
try:s.connect((sys.argv[2],int(sys.argv[3])));s.sendall(b'probe');print(s.recv(100).decode())
except OSError:print('unreachable')
finally:s.close()
'''
def probe(node,proto,host,port):return ns(node,'python3','-c',client,proto,host,str(port))
def rules(lines):
 text='flush chain inet qa incoming\n'+''.join('add rule inet qa incoming '+line+'\n' for line in lines)
 ns('s','nft','-f','-',input=text)
try:
 for node in names:
  run(['ip','netns','add',names[node]]);created.append(names[node]);ns(node,'ip','link','set','lo','up')
 for left,right,lname,rname in [('s','r','vpn','rwan'),('s','e','wan','ewan')]:
  first='qa'+tag+lname;second='qb'+tag+rname
  run(['ip','link','add',first,'type','veth','peer','name',second])
  run(['ip','link','set',first,'netns',names[left]]);run(['ip','link','set',second,'netns',names[right]])
  ns(left,'ip','link','set',first,'name',lname);ns(right,'ip','link','set',second,'name',rname)
  ns(left,'ip','link','set',lname,'up');ns(right,'ip','link','set',rname,'up')
 for node,dev,addr in [('s','vpn','10.255.220.1/24'),('r','rwan','10.255.220.2/24'),('s','wan','198.18.233.1/30'),('e','ewan','198.18.233.2/30'),('e','lo','198.51.100.53/32')]:ns(node,'ip','addr','add',addr,'dev',dev)
 ns('r','ip','route','add','default','via','10.255.220.1');ns('e','ip','route','add','default','via','198.18.233.1')
 ns('s','ip','route','add','198.51.100.53/32','via','198.18.233.2')
 ns('s','sysctl','-qw','net.ipv4.ip_forward=1')
 base='''table inet qa {
 chain incoming { type nat hook prerouting priority dstnat; policy accept; }
 chain outgoing { type nat hook postrouting priority srcnat; policy accept;
  oifname "wan" masquerade
  iifname "vpn" oifname "vpn" masquerade
 }
}
'''
 ns('s','nft','-f','-',input=base)
 for node,marker,host in [('r','ROUTER','10.255.220.2'),('e','INTERNET','198.51.100.53')]:processes.append(subprocess.Popen(['ip','netns','exec',names[node],'python3','-c',server,marker,host],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
 time.sleep(.2)
 config={'bulk_redirect_v4':True,'users':[{'openmptcprouter':{'vpnremoteip':'10.255.220.2'}}]}
 fixed=render.render_bulk_redirect(config)
 old=[line.removeprefix('fib daddr type local ') for line in fixed]
 rules(old)
 record('old_bulk_rule_hijacks_vpn_dns',probe('r','udp','198.51.100.53',53)!='INTERNET')
 rules(fixed)
 record('bulk_udp_dns_to_internet',probe('r','udp','198.51.100.53',53)=='INTERNET')
 record('bulk_tcp_to_internet',probe('r','tcp','198.51.100.53',18080)=='INTERNET')
 record('bulk_public_udp_forward_preserved',probe('e','udp','198.18.233.1',53)=='ROUTER')
 record('bulk_public_tcp_forward_preserved',probe('e','tcp','198.18.233.1',18080)=='ROUTER')
 record('bulk_udp_hairpin_preserved',probe('r','udp','198.18.233.1',53)=='ROUTER')
 record('bulk_tcp_hairpin_preserved',probe('r','tcp','198.18.233.1',18080)=='ROUTER')
 config={'users':[{'openmptcprouter':{'vpnremoteip':'10.255.220.2','fw_ports':[{'name':'UPnP DNS','port':'53','proto':'udp','fwtype':'DNAT','family':4},{'name':'UPnP TCP','port':'18080','proto':'tcp','fwtype':'DNAT','family':4}]}}]}
 _,individual=render.render_fw_ports(config);rules(individual)
 record('individual_udp_dns_to_internet',probe('r','udp','198.51.100.53',53)=='INTERNET')
 record('individual_tcp_to_internet',probe('r','tcp','198.51.100.53',18080)=='INTERNET')
 record('individual_public_udp_forward_preserved',probe('e','udp','198.18.233.1',53)=='ROUTER')
 record('individual_public_tcp_forward_preserved',probe('e','tcp','198.18.233.1',18080)=='ROUTER')
 print(json.dumps({'passed':len(checks),'checks':checks,'scope':'real Linux nftables in isolated namespaces; IPv4; no host or customer rules changed'},indent=2))
finally:
 for p in processes:
  p.terminate()
  try:p.wait(timeout=2)
  except subprocess.TimeoutExpired:p.kill();p.wait()
 for name in reversed(created):subprocess.run(['ip','netns','del',name],capture_output=True)
