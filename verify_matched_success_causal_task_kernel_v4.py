from __future__ import annotations

import copy, hashlib, importlib.util, json, py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V = ROOT / "vendor/brain"
R = V / "canonical/runtime/matched_success_causal_task_kernel_v4.py"

EXPECTED = {
 "canonical/runtime/matched_success_causal_task_kernel_v4.py":"f026d6cfb2d66311de81c19fc14dcc5e335230c6",
 "canonical/tests/test_matched_success_causal_task_kernel_v4.py":"2b9115b83199eaf27eb46dad836b392e86f64c02",
 "canonical/governance/MATCHED_SUCCESS_CAUSAL_TASK_KERNEL_V4.json":"37783ab10e5aad82975f0a0b051059e2b4f7aecc",
}

def blob(p):
    d=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def load_runtime():
    spec=importlib.util.spec_from_file_location("v4",R)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m

def rebind(m,c):
    ph=m._sha(c["case_payload"]); c["case_payload_sha256"]=ph
    s=c["case_initial_state"]
    s["mutable_namespace"]=m._sha({"version":m.VERSION,"case_id":c["case_id"],"payload":ph})
    c["case_initial_state_sha256"]=m._sha(s)

for rel,expected in EXPECTED.items():
    actual=blob(V/rel)
    assert actual==expected,(rel,actual,expected)

py_compile.compile(str(R),doraise=True)
m=load_runtime()
rows=m.generate_cases("VERIFY_COMMITMENT","VERIFY_BEACON")
assert len(rows)==40
assert len({r["case_id"] for r in rows})==40
assert len({r["case_payload_sha256"] for r in rows})==40
assert len({r["case_initial_state_sha256"] for r in rows})==40

atoms=set()
classes=set()
for row in rows:
    assert row["case_payload_sha256"]==m._sha(row["case_payload"])
    assert row["case_initial_state_sha256"]==m._sha(row["case_initial_state"])
    s=row["case_initial_state"]
    assert s["cross_case_memory"] is None and s["result_history"]==[]
    assert s["mutable_namespace"]==m._sha({
        "version":m.VERSION,"case_id":row["case_id"],
        "payload":row["case_payload_sha256"],
    })
    out=m.verify_case_coverage(row)
    assert out["status"]=="PASS__STRUCTURAL_SEMANTIC_COVERAGE",out
    assert out["terminal_result_used"] is False
    atoms.update(out["covered_atoms"]); classes.add(out["class_id"])

assert atoms==set(m.ATOM_CLASS) and len(atoms)==10
assert classes==set(m.CLASS_ATOMS) and len(classes)==7

# stale bytes fail before semantic promotion
x=copy.deepcopy(rows[0])
x["case_payload"]["definition"]["intervention"]["rescue_must_restore_final_acceptance"]=False
o=m.verify_case_coverage(x)
assert o["status"]=="FAIL_CLOSED"
assert "CASE_PAYLOAD_SHA256_MISMATCH" in o["errors"][0]

# re-content-addressed semantic downgrade still fails
rebind(m,x)
o=m.verify_case_coverage(x)
assert o["status"]=="FAIL_CLOSED"
assert "INTERVENTION_RESCUE_NOT_REQUIRED" in o["errors"][0]

# forged coverage label still fails after valid rehash
y=copy.deepcopy(rows[0])
y["case_payload"]["class_atoms"].append("dimension:forged_atom")
rebind(m,y)
o=m.verify_case_coverage(y)
assert o["status"]=="FAIL_CLOSED"
assert "CLASS_ATOM_SET_MISMATCH" in o["errors"][0]

# deterministic, beacon-sensitive
a=m.generate_case(sorted(m.ATOM_CLASS)[0],0,"C","B1")
b=m.generate_case(sorted(m.ATOM_CLASS)[0],0,"C","B1")
c=m.generate_case(sorted(m.ATOM_CLASS)[0],0,"C","B2")
assert a==b and a["case_payload_sha256"]!=c["case_payload_sha256"]

g=json.loads((V/"canonical/governance/MATCHED_SUCCESS_CAUSAL_TASK_KERNEL_V4.json").read_text())
for k in ("execution_authority","promotion_authority","fresh_reality_authority"):
    assert g[k] is False
for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
    assert g["accounting"][k]==0

print(json.dumps({
 "status":"PASS","exact_blob_count":3,"case_count":40,
 "normalized_atom_count":10,"class_count":7,
 "stale_hash_rejected":True,"semantic_downgrade_rejected":True,
 "forged_atom_rejected":True,"terminal_result_used":False,
 "fresh_reality_authority":False
},sort_keys=True))
