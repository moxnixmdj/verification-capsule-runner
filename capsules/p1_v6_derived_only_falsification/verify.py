from __future__ import annotations
import hashlib, importlib.util, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[2]
CAND=ROOT/"capsules/p1_typed_ir_v6_forward_causal_rescue/candidate.py"
PROOF=ROOT/"capsules/p1_typed_ir_v6_forward_causal_rescue/proof.py"
BIND=ROOT/"canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
CONTRACT=ROOT/"capsules/p1_trajectory_t0_t2/canonical/governance/FOUR_UNCOVERED_BEHAVIORAL_PROOF_CONTRACTS_V1.json"

def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

assert blob(CAND)=="18d4de68ee8352410e986c318868642333ec085a"
assert blob(PROOF)=="0f41a36e6ad16722ce05b180e036fb921a2ef886"
assert blob(BIND)=="8703c6aa08227467a619a7ae90d0d61f8e54da39"
assert blob(CONTRACT)=="8c7ffe3d9ff789eddd286496f6de3ce84472c909"

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
candidate=load("v6_candidate",CAND)
proof=load("v6_proof",PROOF)

binding=json.loads(BIND.read_text())
contract=json.loads(CONTRACT.read_text())
p1=[x for x in contract["obligations"] if x.get("behavior_id")=="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"][0]
assert p1["universe"]=="INTERVENTION_IDENTIFIED_REPLAYABLE_AGENT_TRAJECTORIES_WITH_HIDDEN_FAULT_METADATA"
assert "SYMPTOM_ONLY_REPAIR_DOES_NOT_COUNT" in p1["oracle"]
assert "SHIFT_TO_DOWNSTREAM_SYMPTOM" in p1["mutations"]
req=set(binding["evaluator"]["required_checks"])
assert "SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT" in req
assert "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM" in req
assert "DROP_CAUSAL_PREDECESSOR_IN_MULTI_STEP_CHAIN" in set(binding["evaluator"]["required_mutations"])

public={
 "schema":"PROJECT_BRAIN_TRAJECTORY_CAUSAL_IR_PROOF_V6",
 "behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
 "task":{
  "domain":"CODE",
  "trajectory":[
   {"step":0,"action_id":"A0","domain":"CODE","reads":[],"writes":["code:upstream"],"depends_on":[],"dependency_composition":"SEQUENTIAL",
    "checks":[{"kind":"INVARIANT","id":"A0:INVARIANT","pass":True,"evidence":["receipt:A0","check:A0:INVARIANT"],"failure_semantics":"DIRECT_CONTRACT"}]},
   {"step":1,"action_id":"A1","domain":"CODE","reads":["code:upstream"],"writes":["code:symptom"],"depends_on":["A0"],"dependency_composition":"SEQUENTIAL",
    "checks":[
      {"kind":"INVARIANT","id":"A1:INVARIANT:baseline","pass":True,"evidence":["receipt:A1","check:A1:INVARIANT:baseline"],"failure_semantics":"DIRECT_CONTRACT"},
      {"kind":"SCOPE","id":"A1:SCOPE","pass":False,"evidence":["receipt:A1","check:A1:SCOPE"],"failure_semantics":"DERIVED_UPSTREAM"}]},
   {"step":2,"action_id":"A2","domain":"CODE","reads":["code:symptom"],"writes":["code:terminal"],"depends_on":["A1"],"dependency_composition":"SEQUENTIAL",
    "checks":[{"kind":"INVARIANT","id":"A2:INVARIANT","pass":True,"evidence":["receipt:A2","check:A2:INVARIANT"],"failure_semantics":"DIRECT_CONTRACT"}]}
  ],
  "terminal_failed_resources":["code:terminal"],
  "goal":"LOCALIZE_CAUSAL_ROOT_AND_NOMINATE_CONTRACT_REPAIR_WITH_MACHINE_VERIFIED_TERMINAL_RESCUE"
 }
}
failed=[c for r in public["task"]["trajectory"] for c in r["checks"] if c["pass"] is False]
assert len(failed)==1 and failed[0]["failure_semantics"]=="DERIVED_UPSTREAM"
out=candidate.solve(public)
iv=proof.execute_intervention(public,out)
assert out["status"]=="IDENTIFIED",out
assert out["cause_action_id"]=="A1",out
assert out["repair_targets"]==["restore:A1:SCOPE"],out
assert iv["terminal_rescued"] is False,iv
print(json.dumps({
 "status":"PASS__V6_DERIVED_ONLY_SCOPE_COUNTEREXAMPLE_CONFIRMED",
 "candidate_output":out,
 "forward_intervention":iv,
 "source_contract_downstream_symptom_requirement":True,
 "v6_exact_or_superset_terminal_scope_transport_falsified":True,
 "terminal_results_replayed":0,
 "new_reality_units_consumed":0,
 "capability_credit_delta":0,
 "family_credit_delta":0
},indent=2,sort_keys=True))
