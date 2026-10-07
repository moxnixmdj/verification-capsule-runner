from __future__ import annotations
import hashlib, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from canonical.runtime.symbolic_admission_predicate_successor_v1 import (
    admit_manifest, evaluate_expression, expression_sha256, validate_expression
)

def git_blob_sha(p: pathlib.Path) -> str:
    raw=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

runtime=ROOT/"canonical/runtime/symbolic_admission_predicate_successor_v1.py"
tests=ROOT/"canonical/tests/test_symbolic_admission_predicate_successor_v1.py"
assert git_blob_sha(runtime)=="c2f23feb71c233d265344337f3e588fee161f169"
assert git_blob_sha(tests)=="fd235348907956240156b23947c7fd9e4d3bd7db"

expr={"op":"AND","args":[
    {"op":"EQ","path":["task","kind"],"value":"code"},
    {"op":"IN","path":["task","risk"],"values":["low","medium"]},
]}
digest=expression_sha256(expr)
manifest={
    "predicate_id":"P-INDEPENDENT-VERIFY",
    "scope_id":"scope://opus55/observable-trace",
    "route_id":"brain-owned-independent-route",
    "adequacy_certificate_blob_sha":"a"*40,
    "expression":expr,
    "expression_sha256":digest,
    "admission_soundness_receipt":{
        "independent_verified":True,
        "exact_byte_bound":True,
        "conclusion":"success",
        "admission_implies_route_adequacy":True,
        "predicate_id":"P-INDEPENDENT-VERIFY",
        "scope_id":"scope://opus55/observable-trace",
        "route_id":"brain-owned-independent-route",
        "expression_sha256":digest,
        "adequacy_certificate_blob_sha":"a"*40,
    },
}
out=admit_manifest(manifest)
assert out["pass"] is True and out["executable"] is True and out["soundness_authenticated"] is True
assert out["selected_cover_complete_authorized"] is False
assert out["u_empty_authorized"] is False
assert out["terminal_authority"] is False
assert evaluate_expression(expr,{"task":{"kind":"code","risk":"low"}}) is True
assert evaluate_expression(expr,{"task":{"kind":"code","risk":"high"}}) is False
assert evaluate_expression(expr,{"task":{"kind":"other","risk":"low"}}) is False

# Receipt cannot float across expression, route, scope, adequacy bytes, or predicate id.
for field,value in [
    ("expression",{"op":"TRUE"}),
    ("route_id","different-route"),
    ("scope_id","scope://wrong"),
    ("adequacy_certificate_blob_sha","b"*40),
    ("predicate_id","different-predicate"),
]:
    p=json.loads(json.dumps(manifest))
    p[field]=value
    if field=="expression":
        p["expression_sha256"]=expression_sha256(value)
    o=admit_manifest(p)
    assert o["pass"] is False, (field,o)

# Digest tampering fails.
p=json.loads(json.dumps(manifest)); p["expression_sha256"]="sha256:"+"0"*64
o=admit_manifest(p); assert o["pass"] is False and o["reason"]=="EXPRESSION_DIGEST_MISMATCH"

# Dynamic/eval-like operators are rejected.
for bad in [
    {"op":"PYTHON_EVAL","code":"True"},
    {"op":"AND","args":[]},
    {"op":"IN","path":["x"],"values":[]},
    {"op":"EQ","path":[],"value":1},
]:
    ok,_=validate_expression(bad)
    assert ok is False

# Any missing independent/soundness premise fails.
for field in ["independent_verified","exact_byte_bound","admission_implies_route_adequacy"]:
    p=json.loads(json.dumps(manifest)); p["admission_soundness_receipt"][field]=False
    assert admit_manifest(p)["pass"] is False
p=json.loads(json.dumps(manifest)); p["admission_soundness_receipt"]["conclusion"]="failure"
assert admit_manifest(p)["pass"] is False

# No malformed context may accidentally admit.
try:
    evaluate_expression({"op":"TRUE"},[])
except ValueError:
    pass
else:
    raise AssertionError("non-mapping context admitted")

print(json.dumps({
 "schema":"PROJECT_BRAIN_SYMBOLIC_ADMISSION_PREDICATE_SUCCESSOR_INDEPENDENT_VERIFY_V1",
 "status":"PASS",
 "exact_runtime_blob":git_blob_sha(runtime),
 "exact_test_blob":git_blob_sha(tests),
 "positive_case":True,
 "negative_region_cases":2,
 "receipt_binding_mutations_rejected":5,
 "invalid_expression_cases_rejected":4,
 "soundness_premise_mutations_rejected":4,
 "malformed_context_fail_closed":True,
 "selected_cover_complete_authorized":False,
 "u_empty_authorized":False,
 "terminal_authority":False,
 "terminal_credit_delta":0
},sort_keys=True))
