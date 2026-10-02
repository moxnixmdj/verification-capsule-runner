from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py":"2a8613ddac7402c7e6d2f349f9d3c32d3fb95e1d",
 "canonical/runtime/trajectory_failure_typed_ir_proof_v5.py":"3fc600a8176dac250219e3d98b92cf93d8fceef5",
 "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py":"86fb42c09a12db8a510c9708e2e02205a60b73d1",
 "canonical/tests/test_trajectory_failure_typed_ir_v6.py":"aec530d93de315fb692a550bda611139f06b83de",
 "canonical/governance/P1_EXECUTION_REPLAY_INTERVENTION_ENVELOPE_V6.json":"e491e2a461d3a6e2ffe8ce84d81d388a899a1ffa",
 "canonical/governance/P1_V5_RESCUE_CLAIM_QUARANTINE_V1.json":"c52a1423b942af096453f18a8fec0165e49cdfc1",
}

def blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

for rel,want in EXPECTED.items():
    got=blob(ROOT/rel)
    assert got==want,(rel,got,want)

gov=json.loads((ROOT/"canonical/governance/P1_EXECUTION_REPLAY_INTERVENTION_ENVELOPE_V6.json").read_text())
quarantine=json.loads((ROOT/"canonical/governance/P1_V5_RESCUE_CLAIM_QUARANTINE_V1.json").read_text())
assert gov["residual_target"]=="P1_HETEROGENEOUS_INTERVENTION_RESCUE"
assert gov["scope"]["cross_product_case_count"]==192
assert gov["new_reality_units_consumed"]==0
assert gov["capability_credit_delta"]==0
assert gov["family_credit_delta"]==0
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False
assert quarantine["adversarial_verification"]["conclusion"]=="success"
assert "P1_HETEROGENEOUS_INTERVENTION_RESCUE_DISCHARGE_FROM_V5" in quarantine["revoked_or_quarantined"]

subprocess.run([
    sys.executable,"-m","unittest",
    "canonical.tests.test_trajectory_failure_typed_ir_v6","-v"
],cwd=ROOT,check=True)

sys.path.insert(0,str(ROOT))
from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as proof

src=inspect.getsource(proof.execute_after_intervention)
for literal in ['case.get("task")','task.get("trajectory")','task.get("terminal_failed_resources")']:
    assert literal in src,literal
assert "required_root_repairs" not in src

candidate_src=(ROOT/"canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py").read_text()
assert "_fault_injections" not in candidate_src
assert "trajectory_failure_typed_ir_proof_v6" not in candidate_src

cases=proof.suite_cases()
assert len(cases)==192
passed=0
scope_cases=0
rescued_identifiable=0
ambiguous_equivalent=0
for case in cases:
    public=proof.public_task(case)
    assert "_oracle" not in public and "_fault_injections" not in public
    out=candidate.solve(public)
    verdict=proof.score_case(case,out)
    assert verdict.get("pass") is True,(case["seed"],verdict,out)
    passed+=1
    if case["_oracle"]["mechanisms"]["A1"][0]=="SCOPE":
        scope_cases+=1
    if out["status"] in {"IDENTIFIED","INTERACTION"}:
        baseline=proof.execute_after_intervention(case,[])
        repaired=proof.execute_after_intervention(case,out["repair_targets"])
        assert baseline["valid"] and baseline["rescued"] is False
        assert repaired["valid"] and repaired["rescued"] is True
        rescued_identifiable+=1
    else:
        for aid in case["_oracle"]["roots"]:
            repairs=[proof._repair_target(aid,k) for k in case["_oracle"]["mechanisms"][aid]]
            iv=proof.execute_after_intervention(case,repairs)
            assert iv["valid"] and iv["rescued"] is True
        ambiguous_equivalent+=1

assert passed==192
assert scope_cases==24
assert rescued_identifiable==144
assert ambiguous_equivalent==48

# Exact V5 pseudo-rescue counterexample must be dead under V6.
counterexamples=[]
for i,pattern in enumerate(("SINGLE","DELAYED","INTERACTION")):
    case=proof.generate_case(99000+i,pattern=pattern,domain="CODE",kind="SCOPE")
    repairs=proof._expected_root_repairs(case)
    live=proof.execute_after_intervention(case,repairs)
    assert live["valid"] and live["rescued"]

    broken=copy.deepcopy(case)
    broken["task"]["trajectory"]=[]
    deleted_trajectory=proof.execute_after_intervention(broken,repairs)
    assert deleted_trajectory["valid"] is False and deleted_trajectory["rescued"] is False

    taskless=copy.deepcopy(case)
    del taskless["task"]
    deleted_task=proof.execute_after_intervention(taskless,repairs)
    assert deleted_task["valid"] is False and deleted_task["rescued"] is False

    bad_terminal=copy.deepcopy(case)
    bad_terminal["task"]["terminal_failed_resources"]=["nonexistent:terminal"]
    corrupt_terminal=proof.execute_after_intervention(bad_terminal,repairs)
    assert corrupt_terminal["valid"] is False and corrupt_terminal["rescued"] is False

    counterexamples.append({
        "pattern":pattern,
        "live_repair_rescued":live["rescued"],
        "deleted_trajectory_rescued":deleted_trajectory["rescued"],
        "deleted_task_rescued":deleted_task["rescued"],
        "corrupt_terminal_rescued":corrupt_terminal["rescued"],
    })

print(json.dumps({
 "status":"PASS__P1_V6_EXECUTION_REPLAY_KILLS_V5_PSEUDO_RESCUE",
 "exact_brain_blob_count":len(EXPECTED),
 "typed_case_count":passed,
 "explicit_scope_case_count":scope_cases,
 "execution_rescue_identifiable_or_interaction_count":rescued_identifiable,
 "ambiguous_execution_equivalence_case_count":ambiguous_equivalent,
 "v5_pseudo_rescue_counterexamples_killed":counterexamples,
 "candidate_hidden_fault_model_visible":False,
 "terminal_results_replayed":0,
 "new_reality_units_consumed":0,
 "capability_credit_delta":0,
 "family_credit_delta":0
},indent=2,sort_keys=True))
