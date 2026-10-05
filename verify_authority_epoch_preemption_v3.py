from __future__ import annotations
import hashlib, json, pathlib, re, sys

ROOT=pathlib.Path(__file__).resolve().parent
SUBJECT=ROOT/"subject"/"authority_epoch_preemption_v3"
MANIFEST=SUBJECT/"canonical"/"governance"/"AUTHORITY_EPOCH_PREEMPTION_V3.json"
RUNTIME=SUBJECT/"canonical"/"runtime"/"authority_epoch_guard_v1.py"
TESTS=SUBJECT/"canonical"/"tests"/"test_authority_epoch_guard_v1.py"

EXPECTED={
    MANIFEST:"89a4d783e27e43283c2480bac2f10b915fbbfedd",
    RUNTIME:"9f7f06db978a9670e01b080de37b50dc04873361",
    TESTS:"75fd5b920f129aca2b2a37a621867565296ea7e7",
}
def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def fail(x): raise SystemExit("VERIFY_FAIL:"+x)
for p,s in EXPECTED.items():
    g=blob(p)
    if g!=s: fail(f"BLOB:{p.name}:{g}:{s}")

m=json.loads(MANIFEST.read_text())
if m.get("schema")!="PROJECT_BRAIN_AUTHORITY_EPOCH_PREEMPTION_V3": fail("SCHEMA")
if m.get("execution_authority") is not False or m.get("promotion_authority") is not False or m.get("fresh_reality_authority") is not False: fail("AUTHORITY_NONZERO")
components=m.get("epoch_components")
if not isinstance(components,dict) or len(components)!=5: fail("COMPONENTS")
if "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V14_ACTIVATION_V1.json" not in components: fail("V14_ACTIVATION_NOT_BOUND")
if "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V14.json" not in components: fail("V14_CUT_NOT_BOUND")
for p,s in components.items():
    if not isinstance(p,str) or not re.fullmatch(r"[0-9a-f]{40}",str(s)): fail("BAD_COMPONENT:"+repr((p,s)))
payload="".join(f"{p}={s}\n" for p,s in sorted(components.items()))
calc=hashlib.sha256(payload.encode()).hexdigest()
if calc!=m.get("start_authority_epoch_sha256"): fail("EPOCH_HASH:"+calc)
if m.get("status","").startswith("ACTIVE"): fail("CANDIDATE_MUST_NOT_SELF_ACTIVATE")
sys.path.insert(0,str(SUBJECT))
from canonical.runtime.authority_epoch_guard_v1 import compute_epoch, select_latest_active_activation, AuthorityEpochError
if compute_epoch(components)!=calc: fail("RUNTIME_EPOCH_MISMATCH")
rows=[(13,"v13",{"scheduling_authority":True}),(14,"v14",{"scheduling_authority":True}),(15,"v15",{"scheduling_authority":False})]
if select_latest_active_activation(rows)[:2]!=(14,"v14"): fail("LATEST_ACTIVE_SELECTION")
mut=dict(components); k=next(iter(mut)); mut[k]="0"*40
if compute_epoch(mut)==calc: fail("MUTATION_NOT_DETECTED")
try:
    compute_epoch({"x":"bad"})
except AuthorityEpochError:
    pass
else:
    fail("INVALID_SHA_NOT_REJECTED")
print(json.dumps({"schema":"PROJECT_BRAIN_AUTHORITY_EPOCH_PREEMPTION_V3_INDEPENDENT_VERIFICATION","pass":True,"subject_blobs":{p.name:s for p,s in EXPECTED.items()},"epoch_sha256":calc,"component_count":len(components),"v14_bound":True,"adversarial_checks":["INACTIVE_NEWER_DOES_NOT_PREEMPT","ANY_COMPONENT_DELTA_CHANGES_EPOCH","INVALID_COMPONENT_FAILS_CLOSED"],"execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False},sort_keys=True))
