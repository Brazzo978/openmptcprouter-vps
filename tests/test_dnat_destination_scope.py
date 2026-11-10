"""Guard Internet egress against bulk and per-port DNAT, including DNS."""
import importlib.util
from pathlib import Path
import pytest
path=Path(__file__).resolve().parents[1]/'admin/omr_profile_firewall.py'
spec=importlib.util.spec_from_file_location('dnat_renderer',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

@pytest.mark.parametrize('family',[4,6])
@pytest.mark.parametrize('proto',['tcp','udp'])
def test_bulk_requires_local_destination(family,proto):
 config={'users':[{'openmptcprouter':{'userid':0,'vpnremoteip':'10.255.220.2'}}],f'bulk_redirect_v{family}':True}
 rules=module.render_bulk_redirect(config)
 rule=next(r for r in rules if f' {proto} dport' in r)
 assert rule.startswith('fib daddr type local ')
 assert 'iifname' not in rule  # VPN -> VPS-address hairpin remains eligible.

@pytest.mark.parametrize('family',[4,6])
@pytest.mark.parametrize('proto',['tcp','udp'])
def test_individual_dnat_including_upnp_requires_local_destination(family,proto):
 config={'users':[{'openmptcprouter':{'vpnremoteip':'10.255.220.2','fw_ports':[{'name':'UPnP test','port':'53','proto':proto,'fwtype':'DNAT','family':family}]}}]}
 accepts,rules=module.render_fw_ports(config)
 assert not accepts and len(rules)==1
 assert rules[0].startswith('fib daddr type local ')

def test_input_accept_rules_keep_their_existing_scope():
 config={'users':[{'openmptcprouter':{'fw_ports':[{'port':'65443','proto':'udp','fwtype':'ACCEPT','family':4}]}}]}
 accepts,dnat=module.render_fw_ports(config)
 assert not dnat and len(accepts)==1 and 'fib daddr' not in accepts[0]

def test_explicit_destination_source_and_target_are_preserved():
 config={'users':[{'openmptcprouter':{'fw_ports':[{'port':'80','proto':'tcp','fwtype':'DNAT','family':4,'source_dip':'203.0.113.2','dest_ip':'198.51.100.8','vpn':'10.255.249.2'}]}}]}
 _,rules=module.render_fw_ports(config)
 assert 'ip daddr 203.0.113.2 ip saddr 198.51.100.8' in rules[0]
 assert 'dnat ip to 10.255.249.2' in rules[0]
