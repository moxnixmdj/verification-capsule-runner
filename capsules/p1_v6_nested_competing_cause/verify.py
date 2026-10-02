from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED_BLOB="18d4de68ee8352410e986c318868642333ec085a"

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

assert blob(ROOT/"candidate_v6.py")==EXPECTED_BLOB

spec=importlib.util.spec_from_file_location("candidate_v6",ROOT/"candidate_v6.py")
candidate=importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(candidate)

def check(kind,aid,passed):
    return {"kind":kind,"id":f"{aid}:{kind}","pass":passed,
            "evidence":[f"receipt:{aid}",f"check:{aid}:{kind}"]}

# Same public trace under two incompatible causal worlds.
# A1 and A2 both visibly fail direct checks and lie on the terminal dependency chain.
# The frozen P1 contract does not say every visible failed check is causally load-bearing.
public={
  "task":{
    "domain":"CODE",
    "trajectory":[
      {"step":0,"action_id":"A0","reads":[],"writes":["seed"],"depends_on":[],
       "dependency_composition":"SEQUENTIAL","checks":[check("INVARIANT","A0",True)]},
      {"step":1,"action_id":"A1","reads":["seed"],"writes":["mid1"],"depends_on":["A0"],
       "dependency_composition":"SEQUENTIAL","checks":[check("INVARIANT","A1",True),check("AUTHORITY","A1",False)]},
      {"step":2,"action_id":"A2","reads":["mid1"],"writes":["mid2"],"depends_on":["A1"],
       "dependency_composition":"SEQUENTIAL","checks":[check("INVARIANT","A2",True),check("PROVENANCE","A2",False)]},
      {"step":3,"action_id":"A3","reads":["mid2"],"writes":["terminal"],"depends_on":["A2"],
       "dependency_composition":"SEQUENTIAL","checks":[check("INVARIANT","A3",True)]},
    ],
    "terminal_failed_resources":["terminal"],
    "goal":"LOCALIZE_CAUSAL_ROOT_AND_NOMINATE_CONTRACT_REPAIR_WITH_MACHINE_VERIFIED_TERMINAL_RESCUE"
  }
}

out=candidate.solve(public)
assert out["status"]=="IDENTIFIED",out
assert out["cause_action_id"]=="A1",out
assert out["repair_targets"]==["restore:A1:AUTHORITY"],out

# Hidden structural worlds compatible with exactly the same public trace.
# A visible failed check can be incidental rather than the load-bearing latent fault.
WORLD_UPSTREAM=("A1","AUTHORITY")
WORLD_DOWNSTREAM=("A2","PROVENANCE")

def rescued(world_fault,repairs):
    parsed=set()
    for raw in repairs:
        parts=raw.split(":")
        if len(parts)==3 and parts[0]=="restore":
            parsed.add((parts[1],parts[2]))
    # Repaired latent fault restores the causal chain; repairing the other
    # visible failure leaves the actual latent fault active.
    return world_fault in parsed

v6_repairs=out["repair_targets"]
vector=(rescued(WORLD_UPSTREAM,v6_repairs),rescued(WORLD_DOWNSTREAM,v6_repairs))
assert vector==(True,False),vector

alt=["restore:A2:PROVENANCE"]
alt_vector=(rescued(WORLD_UPSTREAM,alt),rescued(WORLD_DOWNSTREAM,alt))
assert alt_vector==(False,True),alt_vector

# No unique repair rescues both compatible worlds. A unique-cause answer is
# therefore an epistemic overclaim; P1's frozen nonidentifiability rule requires
# ambiguity / an information request.
assert not all(vector)
assert not all(alt_vector)

print(json.dumps({
  "status":"PASS__COUNTEREXAMPLE_REPRODUCED",
  "exact_brain_candidate_blob":EXPECTED_BLOB,
  "public_trace_identical_across_hidden_worlds":True,
  "candidate_status":out["status"],
  "candidate_cause":out["cause_action_id"],
  "candidate_repair":v6_repairs,
  "candidate_repair_world_rescue_vector":vector,
  "alternative_repair_world_rescue_vector":alt_vector,
  "required_truthful_status":"AMBIGUOUS_OR_INFORMATION_REQUEST",
  "finding":"V6_ROOT_BY_FAILED_ANCESTRY_CAN_OVERCLAIM_UNIQUE_CAUSE_WHEN_NESTED_VISIBLE_FAILURES_HAVE_INCOMPATIBLE_HIDDEN_CAUSAL_WORLDS",
  "terminal_results_replayed":0,
  "new_reality_units_consumed":0,
  "capability_credit_delta":0,
  "family_credit_delta":0
},indent=2,sort_keys=True))
