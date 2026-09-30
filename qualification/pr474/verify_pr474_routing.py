#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED_BROAD="1efaec4ba51ecb5c40072b3190853f4de89d8f77"
EXPECTED_GROUND="46e8e7466479ea298c34e5fa682d49c374510ce9"

def blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(name):
    p=ROOT/(name+".py")
    spec=importlib.util.spec_from_file_location("oracle_"+name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

bp=ROOT/"broad_objective_decompose.py"
gp=ROOT/"plain_goal_bound_grounding.py"
assert blob_sha(bp)==EXPECTED_BROAD,(blob_sha(bp),EXPECTED_BROAD)
assert blob_sha(gp)==EXPECTED_GROUND,(blob_sha(gp),EXPECTED_GROUND)
broad=load("broad_objective_decompose")
ground=load("plain_goal_bound_grounding")

EXPECTED_ROLES=[
 "SOURCE_DISCOVERY","EVIDENCE_ACQUISITION","EVIDENCE_EXTRACTION",
 "RELATION_EVALUATION","DECISION_SYNTHESIS_AND_VERIFICATION"
]

fresh=[
 ("Assess whether battery pack specific energy increased more from 2022 to 2026 than from 2018 to 2022. "
  "Use authoritative primary technical evidence. Autonomously discover and verify relevant sources, "
  "choose and run a zero-cost verification method, identify material scope limitations, independently "
  "verify the consequential result, and produce a provenance-bearing decision-quality answer."),
 ("Determine whether reported coastal sea-level rise accelerated in the latest measured interval relative "
  "to the preceding interval. Use authoritative primary evidence and a real executable check. Autonomously "
  "discover and verify relevant sources, choose and execute a zero-cost verification method, identify "
  "interpretation limitations, independently verify the consequential result, and produce a decision-quality answer.")
]
for objective in fresh:
    direct=broad.decompose(objective)
    assert direct["status"]=="DECOMPOSED",direct
    assert [x["role"] for x in direct["roles"]]==EXPECTED_ROLES,direct
    assert direct["model_dependency_count"]==0,direct
    out=ground.ground(objective,{})
    assert len(out["clauses"])>1,out
    assert out["grounded_clause_count"]==0,out
    assert out["unresolved_clause_indexes"]==list(range(len(out["clauses"]))),out
    assert out["broad_objective_decomposition_available"] is True,out
    assert [x["role"] for x in out["broad_objective_decomposition"]["roles"]]==EXPECTED_ROLES,out

for objective in [
 "Assess whether two measured values differ. Run python verify_values.py",
 "Evaluate whether two measurements differ. Execute ./check_values.sh",
 "Compare two measurements using https://example.com/data"
]:
    out=broad.decompose(objective)
    assert out["status"]=="UNSUPPORTED",out
    assert out["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE",out

registry={
 "battery.voltage.measurement":{
   "status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,
   "provides":["battery voltage measurement"],"requires":[],
   "keywords":["battery","voltage","measurement"],
   "source":{"type":"independent_qualification_fixture"}
 }
}
mixed=("Assess battery voltage measurement behavior. "
       "Investigate unrelated atmospheric circulation evidence.")
partial=ground.ground(mixed,registry)
assert partial["grounded_clause_count"]>=1,partial
assert partial["broad_objective_decomposition_available"] is False,partial
assert partial["whole_goal_external_discovery_forbidden_if_any_bound_grounding"] is True,partial

print("BRAIN_PR474_INDEPENDENT_ROUTING_QUALIFICATION_PASS")
print("candidate_broad_blob="+EXPECTED_BROAD)
print("candidate_ground_blob="+EXPECTED_GROUND)
print("fresh_objective_count="+str(len(fresh)))
