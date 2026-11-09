"""Exercise the production compatibility parser without starting the API."""
import ast
import ipaddress
from pathlib import Path
import re
import pytest

SOURCE=Path(__file__).resolve().parents[1]/'admin/omradmin.py'
TREE=ast.parse(SOURCE.read_text())
FN=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name=='_normalize_legacy_lan_addresses')
ENV={'ipaddress':ipaddress,'re':re}
exec(compile(ast.Module(body=[FN],type_ignores=[]),str(SOURCE),'exec'),ENV)
normalize=ENV['_normalize_legacy_lan_addresses']

@pytest.mark.parametrize('raw,want',[
 ('10.1.1.1/23/255.255.254.0','10.1.1.1/23'),
 ('10.1.1.1/23/255.255.255.0','10.1.1.1/23'),
 ('10.1.1.1/23/24','10.1.1.1/23'),
 ('10.1.1.1/23','10.1.1.1/23'),
 ('192.168.100.1/255.255.255.0','192.168.100.1/255.255.255.0'),
 ('192.168.100.1','192.168.100.1'),
])
def test_compatible_payloads(raw,want):assert normalize([raw])==[want]

@pytest.mark.parametrize('raw',[
 '10.1.1.1/33/255.255.255.0','10.1.1.1/-1/255.255.255.0',
 '10.1.1.999/23/255.255.254.0','10.1.1.1/23/255.0.255.0',
 '10.1.1.1/23/999','10.1.1.1/23/garbage','10.1.1.1/23/',
 '10.1.1.1/23/255.255.254.0/24','10.1.1.1/255.255.254.0/24',
 'fd00::1/64','10.1.1.1/23;reboot','10.1.1.1/23/255.255.254.0;reboot',
])
def test_malformed_payloads_rejected(raw):
 with pytest.raises(ValueError):normalize([raw])

def test_multiple_and_empty():
 assert normalize([])==[]
 assert normalize(['10.1.1.1/23/255.255.255.0','192.168.8.1/255.255.255.0'])==['10.1.1.1/23','192.168.8.1/255.255.255.0']

def test_model_runs_parser_before_endpoint():
 model=next(n for n in TREE.body if isinstance(n,ast.ClassDef) and n.name=='Lanips')
 validator=next(n for n in model.body if isinstance(n,ast.FunctionDef))
 assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='field_validator' and n.args[0].value=='lanips' for n in validator.decorator_list)
 assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_normalize_legacy_lan_addresses' for n in ast.walk(validator))
