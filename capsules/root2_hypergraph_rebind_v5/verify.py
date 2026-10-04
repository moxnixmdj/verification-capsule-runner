#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
exp=json.loads((ROOT/"EXPECTED.json").read_text())
files={
 "inventory":ROOT/"ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json",
 "vector":ROOT/"ROOT2_FROZEN_COMPARATOR_VECTOR_V1.json",
 "candidate":ROOT/"ROOT2_PROOF_HYPERGRAPH_CURRENT_REBIND_V5.json",
 "root_state":ROOT/"TERMINAL_ROOT_CAUSE_STATE_V1.json",
}
for k,p in files.items():
    assert blob(p)==exp[k+"_blob"],(k,blob(p),exp[k+"_blob"])
inv=json.loads(files["inventory"].read_text())
vec=json.loads(files["vector"].read_text())
cand=json.loads(files["candidate"].read_text())
root=json.loads(files["root_state"].read_text())
preds=[p for s in vec["surfaces"] for p in s["predicates"]]
assert len(vec["surfaces"])==exp["fixed_bar_surfaces"]
assert len(preds)==exp["fixed_bar_predicates"] and len(set(preds))==exp["fixed_bar_predicates"]
assert vec["authority"]["route_inventory_git_blob_sha"]==exp["inventory_blob"]
assert cand["current_inputs"]["route_inventory_git_blob_sha"]==exp["inventory_blob"]
assert cand["current_inputs"]["comparator_vector_git_blob_sha"]==exp["vector_blob"]
assert cand["current_inputs"]["root_state_git_blob_sha"]==exp["root_state_blob"]
part=root["current_residual_root_partition"]
assert part["root2_only_count"]==exp["root2_only"]
assert part["root2_and_root3_count"]==exp["root2_mixed"]
assert exp["root2_only"]+exp["root2_mixed"]==exp["root2_involved"]
assert cand["invariants"]["total_root2_involved_predicates"]==exp["root2_involved"]
assert cand["invariants"]["comparator_targets_changed"] is False
assert cand["invariants"]["predicate_set_changed"] is False
assert cand["invariants"]["optimizer_logic_changed"] is False
osv=[x for x in inv["routes"] if x["surface"]=="OSWorld 2.1 partial"]
assert len(osv)==1
osv=osv[0]
assert osv["partial_metric_semantics"]["removed"]=="PARTIAL_MEANS_AN_UNIDENTIFIED_TASK_SUBSET"
assert "ANTHROPIC_EXACT_RUN_POPULATION_OPEN" in osv["partial_metric_semantics"]["preserved"]
assert "DO_NOT_INFER_ANTHROPIC_RAN_ALL_108_OSWORLD_V21_TASKS" in cand["hard_rules"]
for x in (cand,vec):
    assert x["incremental_spend_usd"]==0
    assert x["acceptance_credit_delta"]==0
    assert x["fresh_reality_authority"] is False
print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT2_HYPERGRAPH_REBIND_V5_PUBLIC_RUNNER_RESULT_V1",
 "status":"PASS__EXACT_CURRENT_INPUTS__15_FIXED_BAR_PREDICATES__14_SURFACES__16_ROOT2_ONLY_PLUS_3_MIXED__OSWORLD_SEMANTICS_BOUND__NO_TARGET_OR_LOGIC_CHANGE__ZERO_CREDIT",
 "pass":True
},sort_keys=True))
