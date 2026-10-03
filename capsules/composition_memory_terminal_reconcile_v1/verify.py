from __future__ import annotations
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()

exp=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
actual={
 "before/CURRENT_TERMINAL_AUTHORITY_V1.json":blob(ROOT/"before.json"),
 "after/CURRENT_TERMINAL_AUTHORITY_V1.json":blob(ROOT/"after.json"),
 "canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V4.json":blob(ROOT/"v4.json"),
 "canonical/verification/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":blob(ROOT/"bridge_verification.json"),
 "canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_PUBLIC_RUNNER_VERIFICATION_20261003_V3.json":blob(ROOT/"slice_verification.json"),
}
assert actual==exp["exact_brain_blobs"],(actual,exp["exact_brain_blobs"])
before=json.loads((ROOT/"before.json").read_text())
after=json.loads((ROOT/"after.json").read_text())
v4=json.loads((ROOT/"v4.json").read_text())
bv=json.loads((ROOT/"bridge_verification.json").read_text())
sv=json.loads((ROOT/"slice_verification.json").read_text())

# Terminal truth and acceptance must not move.
assert before["truth"]==after["truth"]
assert after["truth"]["opus55_acceptance"]=="3/19_PASS__16/19_OPEN"
assert after["truth"]["achieved"] is False
assert before["atomic_acceptance_frontier"]==after["atomic_acceptance_frontier"]
assert after["atomic_acceptance_frontier"]["proved"]==8
assert after["atomic_acceptance_frontier"]["unresolved"]==30
assert before["next"]==after["next"]
assert before["tool_discovery_dynamic_refinement"]==after["tool_discovery_dynamic_refinement"]
assert before["delegation_promotion_reconciliation"]==after["delegation_promotion_reconciliation"]
assert before["causal_cut_admission_policy"]==after["causal_cut_admission_policy"]
assert before["proof_atom_receipt_snapshot_v4"]==after["proof_atom_receipt_snapshot_v4"]

# New pointers must bind exact verified objects.
s=after["sources"]
assert s["composition_component_proof_current_authority_v4"]["git_blob_sha"]==actual["canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V4.json"]
assert s["composition_memory_bridge_v2"]["verification_git_blob_sha"]==actual["canonical/verification/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"]
assert s["composition_component_proof_slice_v3"]["verification_git_blob_sha"]==actual["canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_PUBLIC_RUNNER_VERIFICATION_20261003_V3.json"]
assert "1_OF_12_CURRENTLY_ADMISSIBLE" in s["composition_component_proof_current_authority_v4"]["status"]
assert "EXACTLY_1_OF_12_SCOPED_PROVED_MEMORY" in s["composition_component_proof_slice_v3"]["status"]

assert v4["truth"]["current_admissible_scoped_proved"]==1
assert v4["truth"]["current_open_or_quarantined"]==11
assert v4["truth"]["current_scoped_proved_components"]==["memory"]
assert v4["truth"]["parent_composition_predicate_closed"] is False
assert bv["public_runner"]["conclusion"]=="success"
assert sv["public_runner"]["conclusion"]=="success"
assert sv["verified_result"]["scoped_proved_count"]==1
assert sv["verified_result"]["open_count"]==11
assert sv["verified_result"]["parent_composition_predicate_closed"] is False

# Exact allowed-diff firewall. Normalize only fields this reconciliation is authorized to touch.
b=copy.deepcopy(before)
a=copy.deepcopy(after)
for key in ["composition_memory_bridge_v2","composition_component_proof_slice_v3","composition_component_proof_current_authority_v4"]:
    a["sources"].pop(key,None)

# Revert additive metadata on historical composition source descriptors.
for key in ["composition_component_proof_current_authority_v3","composition_slicer_exhaustion"]:
    for field in ["current_credit_status","superseded_by","superseded_current_slice"]:
        a["sources"].get(key,{}).pop(field,None)

# Revert only the two composition residual rows by semantic slot.
def comp_residual_indices(doc):
    return [i for i,x in enumerate(doc["residual"]) if isinstance(x,str) and ("FROZEN_COMPOSITION_COMPONENT_INTERFACES" in x or "COMPOSITION_SLICER_" in x)]
bi=comp_residual_indices(b); ai=comp_residual_indices(a)
assert bi==ai and len(ai)==2,(bi,ai)
for i in ai: a["residual"][i]=b["residual"][i]

a["integrator_reconciliation_20261002_current"]["composition"]=b["integrator_reconciliation_20261002_current"]["composition"]
suffix="__COMPOSITION_COMPONENT_AUTHORITY_V4_ACTIVE__CURRENT_MEMORY_RECEIPT_INDEPENDENTLY_VERIFIED__1_OF_12_SCOPED_PROVED__11_OPEN__PARENT_COMPOSITION_REMAINS_OPEN__NO_OPUS55_FAMILY_OR_ATOMIC_ACCEPTANCE_DELTA"
assert a["rule"].endswith(suffix)
a["rule"]=a["rule"][:-len(suffix)]

assert a==b,"UNAUTHORIZED_TERMINAL_AUTHORITY_DIFF"

print(json.dumps({
 "status":"PASS",
 "acceptance_preserved":"3_OF_19__8_OF_38",
 "composition_current":"1_OF_12_MEMORY__11_OPEN__PARENT_OPEN",
 "terminal_goal_achieved":False,
 "allowed_diff_firewall":"PASS",
 "new_family_credit":0
},indent=2,sort_keys=True))
