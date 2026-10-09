from __future__ import annotations
import hashlib, importlib.util, json, sys, tempfile, types
from pathlib import Path
from typing import Any, Mapping

ROOT=Path.cwd()
EXPECTED={
"canonical/runtime/certificate_gated_selected_route_runtime_entrypoint_v5.py":"38f3ed4c32fd4f54698267372cc6869204d00bd9",
"canonical/governance/CURRENT_CERTIFICATE_GATED_SELECTED_ROUTE_REGISTRY.json":"16fcc1efc9a50345af895cb8c29114a37f470298",
"canonical/governance/CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_REGISTRY_V3.json":"469c55594a4acf40d7261966580b75ece467a863",
"canonical/runtime/router_deployment_canary_v1.py":"de71202a17071c8af88ec7ac6e1f241fb42854c2",
"canonical/runtime/symbolic_router_deployment_canary_predicate_v1.py":"b8a9ba97dc4a2e11cfbcf03fb36dcaa5ca0e45e6",
"canonical/verification/ROUTER_DEPLOYMENT_CANARY_ADEQUACY_CERTIFICATE_20261007_V1.json":"e521f7b75123bca5cc9704340283a727bb45e957",
"canonical/verification/ROUTER_DEPLOYMENT_CANARY_ADMISSION_CERTIFICATE_20261007_V1.json":"1b2f97e7d46877b8782ea211fd15f679e6bfb5b0",
"canonical/verification/SYMBOLIC_ROUTER_DEPLOYMENT_CANARY_ADEQUACY_CERTIFICATE_20261007_V1.json":"1f87838111c606437442b5d100f57004faf89a05",
"canonical/verification/SYMBOLIC_ROUTER_DEPLOYMENT_CANARY_ADMISSION_CERTIFICATE_20261007_V1.json":"5eda5a3275cb11c273159426ab79565d6d2ceaab"
}

def blob(path):
    p=Path(path); data=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

for path,want in EXPECTED.items():
    got=blob(path)
    assert got==want,(path,want,got)

class RuntimeBindingFailClosed(RuntimeError): pass

def canonical_path(raw,*,prefixes):
    value=str(raw or "").strip(); p=Path(value)
    if not value or p.is_absolute() or ".." in p.parts:
        raise RuntimeBindingFailClosed("NONCANONICAL_PATH")
    if not any(value.startswith(x) for x in prefixes):
        raise RuntimeBindingFailClosed("PATH_OUTSIDE_ALLOWED_CANONICAL_SCOPE")
    full=ROOT/p
    if not full.is_file(): raise RuntimeBindingFailClosed("BOUND_FILE_MISSING:"+value)
    return full

def load_json(path):
    value=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value,Mapping): raise RuntimeBindingFailClosed("BOUND_JSON_NOT_OBJECT")
    return value

def load_callable(path,callable_name,*,module_prefix):
    name=str(callable_name or "").strip()
    if not name: raise RuntimeBindingFailClosed("CALLABLE_MISSING")
    modname=module_prefix+blob(path)
    spec=importlib.util.spec_from_file_location(modname,path)
    if spec is None or spec.loader is None: raise RuntimeBindingFailClosed("IMPORT_SPEC_FAILED")
    module=importlib.util.module_from_spec(spec); sys.modules[modname]=module; spec.loader.exec_module(module)
    fn=getattr(module,name,None)
    if not callable(fn): raise RuntimeBindingFailClosed("CALLABLE_INVALID")
    return fn

def digest(value,label):
    if not isinstance(value,Mapping): raise RuntimeBindingFailClosed(label+"_MAPPING_REQUIRED")
    raw=json.dumps(dict(value),sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()

def context_digest(value): return digest(value,"CONTEXT")
def payload_digest(value): return digest(value,"PAYLOAD")

def validate_payload(row,*,cell_id,context,payload,actual_context_digest):
    req=("payload_validator_path","payload_validator_blob_sha","payload_validator_callable")
    if any(not row.get(k) for k in req): raise RuntimeBindingFailClosed("CREDITABLE_PAYLOAD_VALIDATOR_BINDING_MISSING")
    p=canonical_path(row["payload_validator_path"],prefixes=("canonical/runtime/",))
    if row["payload_validator_blob_sha"]!=blob(p): raise RuntimeBindingFailClosed("PAYLOAD_VALIDATOR_BLOB_DRIFT")
    fn=load_callable(p,row["payload_validator_callable"],module_prefix="capsule_validator_")
    pd=payload_digest(payload); a=fn(dict(context),dict(payload))
    if not isinstance(a,Mapping) or a.get("admitted") is not True: raise RuntimeBindingFailClosed("PAYLOAD_NOT_ADMITTED_TO_SELECTED_CELL")
    if a.get("cell_id")!=cell_id: raise RuntimeBindingFailClosed("PAYLOAD_ATTESTATION_CELL_MISMATCH")
    if a.get("context_digest_sha256")!=actual_context_digest: raise RuntimeBindingFailClosed("PAYLOAD_ATTESTATION_CONTEXT_MISMATCH")
    if a.get("payload_sha256")!=pd: raise RuntimeBindingFailClosed("PAYLOAD_ATTESTATION_DIGEST_MISMATCH")
    return pd

v2=types.ModuleType("canonical.runtime.certificate_gated_selected_route_runtime_entrypoint_v2")
for k,v in {"ROOT":ROOT,"RuntimeBindingFailClosed":RuntimeBindingFailClosed,"_canonical_path":canonical_path,"_load_callable":load_callable,"_load_json":load_json,"_validate_creditable_payload":validate_payload,"context_digest":context_digest,"git_blob_sha":blob}.items():
    setattr(v2,k,v)
sys.modules[v2.__name__]=v2

def cover_state(registry,rows):
    creditable=[r for r in rows if r.get("creditable") is True]
    if not creditable or not isinstance(registry.get("complement_coverage_receipt"),Mapping):
        return {"authorized":False,"gate_status":"NO_CREDITABLE_EXACT_PREDICATE_SET_OR_COMPLEMENT_RECEIPT"}
    return {"authorized":False,"gate_status":"CAPSULE_DOES_NOT_REPROVE_COMPLEMENT_COVER"}

v3=types.ModuleType("canonical.runtime.certificate_gated_selected_route_runtime_entrypoint_v3")
v3._selected_cover_state=cover_state
sys.modules[v3.__name__]=v3

from canonical.runtime import certificate_gated_selected_route_runtime_entrypoint_v5 as v5

source=(ROOT/"canonical/runtime/certificate_gated_selected_route_runtime_entrypoint_v5.py").read_text()
assert "matches.sort" not in source
assert "CURRENT_CERTIFICATE_GATED_SELECTED_ROUTE_REGISTRY.json" in source

p=v5.preflight()
assert p["pass"] is True,p
assert (p["route_row_count"],p["route_id_count"],p["exact_route_count"],p["symbolic_route_count"],p["creditable_route_count"])==(2,1,1,1,0),p
assert p["selected_cover_complete"] is False,p

a=v5.dispatch({"kind":"ROUTER_DEPLOYMENT_CANARY_V1"},{"probe":7})
assert a["match_mode"]=="EXACT_DIGEST" and a["selected_route_id"]=="router-deployment-canary" and a["payload_sha256"] is None,a
b=v5.dispatch({"kind":"SYMBOLIC_ROUTER_DEPLOYMENT_CANARY_V1"},{"probe":8})
assert b["match_mode"]=="SYMBOLIC_PREDICATE" and b["selected_route_id"]=="router-deployment-canary" and b["payload_sha256"] is None,b

try: v5.select_route({"kind":"NO_ROUTE"})
except RuntimeBindingFailClosed as e: assert "NO_CERTIFIED_ROUTE_FOR_ACTUAL_CONTEXT" in str(e)
else: raise AssertionError("UNCOVERED_DID_NOT_FAIL_CLOSED")

old=v5._row_matches; v5._row_matches=lambda row,context,actual_digest: True
try:
    try: v5.select_route({"kind":"FORCE_OVERLAP"})
    except RuntimeBindingFailClosed as e: assert "AMBIGUOUS_CERTIFIED_ROUTE_MATCH" in str(e)
    else: raise AssertionError("OVERLAP_DID_NOT_FAIL_CLOSED")
finally: v5._row_matches=old

with tempfile.TemporaryDirectory() as td:
    bad=json.loads((ROOT/"canonical/governance/CURRENT_CERTIFICATE_GATED_SELECTED_ROUTE_REGISTRY.json").read_text())
    bad["target"]["git_blob_sha"]="0"*40
    pth=Path(td)/"p.json"; pth.write_text(json.dumps(bad))
    try: v5.load_registry(pth)
    except RuntimeBindingFailClosed as e: assert "CURRENT_REGISTRY_TARGET_BLOB_DRIFT" in str(e)
    else: raise AssertionError("POINTER_DRIFT_DID_NOT_FAIL_CLOSED")

try: v5._verify_creditable_payload_binding({"creditable":True,"_admission":{}},0)
except RuntimeBindingFailClosed as e: assert "CREDITABLE_PAYLOAD_VALIDATOR_BINDING_MISSING" in str(e)
else: raise AssertionError("MISSING_VALIDATOR_DID_NOT_FAIL_CLOSED")

calls=[]
orig=(v5.load_registry,v5.select_route,v5._verified_rows,v5._selected_cover_state,v5._load_callable,v5._validate_creditable_payload)
synthetic={"creditable":True,"cell_id":"C","route_id":"R","match_mode":"SYMBOLIC_PREDICATE","admission_predicate_id":"P","route_blob_sha":"a"*40,"adequacy_certificate_blob_sha":"b"*40,"admission_certificate_blob_sha":"c"*40,"_route_path":object()}
try:
    v5.load_registry=lambda:{}
    v5.select_route=lambda context,registry=None:synthetic
    v5._verified_rows=lambda registry:[synthetic]
    v5._selected_cover_state=lambda registry,rows:{"authorized":False,"gate_status":"OPEN"}
    v5._load_callable=lambda *args,**kwargs:(lambda payload:{"pass":True})
    def mark(*args,**kwargs): calls.append(1); return "bound-payload-digest"
    v5._validate_creditable_payload=mark
    out=v5.dispatch({"x":1},{"y":2})
    assert out["payload_sha256"]=="bound-payload-digest" and len(calls)==1,out
finally:
    v5.load_registry,v5.select_route,v5._verified_rows,v5._selected_cover_state,v5._load_callable,v5._validate_creditable_payload=orig

assert v5.verified_route_ids()==["router-deployment-canary"]
print(json.dumps({"status":"PASS__CERTIFIED_ROUTE_CURRENT_REGISTRY_V5_EXACT_CONTROL_LOGIC_ISOLATED_EXECUTION","exact_v5_blob":EXPECTED["canonical/runtime/certificate_gated_selected_route_runtime_entrypoint_v5.py"],"pointer_blob":EXPECTED["canonical/governance/CURRENT_CERTIFICATE_GATED_SELECTED_ROUTE_REGISTRY.json"],"registry_blob":EXPECTED["canonical/governance/CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_REGISTRY_V3.json"],"exact_dispatch":True,"symbolic_dispatch":True,"uncovered_fail_closed":True,"overlap_fail_closed":True,"pointer_hash_drift_fail_closed":True,"creditable_payload_binding_call_path":True,"selected_cover_complete":False,"full_private_repository_regression_verified":False,"terminal_authority":False},sort_keys=True))
