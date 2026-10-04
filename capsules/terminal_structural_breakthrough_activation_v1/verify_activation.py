import hashlib,json
from pathlib import Path
p=Path(__file__).parent
def h(x):
 d=x.read_bytes();return hashlib.sha1(f"blob {len(d)}\0".encode()+d).hexdigest()
a=p/"activation.json";r=p/"current_main_reconciliation.json"
assert h(a)=="575b5541b07e5c4856da5f718a3f5b0c43303d08"
assert h(r)=="afa5770e40c031dadf82b25ce25e2ebe3e3fcead"
A=json.loads(a.read_text());R=json.loads(r.read_text())
assert A["authority"]=={"scheduling":True,"candidate_generation":True,"execution":False,"promotion":False,"fresh_reality":False}
assert A["preserved_authority"]["root2"]=="ROOT2_V11" and A["preserved_authority"]["root3"]=="ROOT3_V2" and A["preserved_authority"]["retrieval"]=="RETRIEVAL_V19"
assert A["preserved_authority"]["fresh_reality_block"] is True and all(v==0 for v in A["accounting"].values())
assert R["reconciled_main"]=="e6d0b29bd27d3a2fa4839ccdb838e21037dd66cf" and R["main_delta"]["proved_atomic"]==12 and R["main_delta"]["unresolved_atomic"]==26
assert R["fresh_reality_authority"] is False and R["execution_authority"] is False and R["promotion_authority"] is False
print('INDEPENDENT_ACTIVATION_SEMANTICS_PASS')
