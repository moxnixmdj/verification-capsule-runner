from __future__ import annotations
import copy, hashlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from canonical.runtime.composition_behavioral_bridge_verifier_v1 import evaluate,git_blob_sha

EXPECTED={
  "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json": "ee187f611a0e82b2de495ee377682f39bc31dd31",
  "canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json": "96052a6b5178305b37a2526fb25c3f53fa33b9b5",
  "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json": "9efbf3e81e67fbd15e34be2fcd86fbfc626b246d",
  "canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json": "d6cb17f548493e64ca3d200d51b049412a939ef7",
  "canonical/runtime/composition_behavioral_bridge_verifier_v1.py": "d6bfd80bab2742332ceb3c4105e535202ae00b20",
  "canonical/tests/test_composition_behavioral_bridge_v1.py": "1b768b99f1db6664ed078e6ffa2e1d522ffb59b1"
}
for rel,sha in EXPECTED.items():
    assert git_blob_sha(ROOT/rel)==sha,(rel,git_blob_sha(ROOT/rel),sha)

reg=json.loads((ROOT/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json").read_text())
trans=json.loads((ROOT/"canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json").read_text())
man=json.loads((ROOT/"canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json").read_text())
bridge=json.loads((ROOT/"canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json").read_text())
shas={
 "registry":git_blob_sha(ROOT/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
 "transmutation":git_blob_sha(ROOT/"canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json"),
 "manifest":git_blob_sha(ROOT/"canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json")
}
out=evaluate(reg,trans,man,bridge,shas)
assert out["pass"] is True,out
assert out["derived_binding_count"]==2,out
assert {x["component_id"] for x in out["derived_bindings"]}=={"delegation","tool discovery"},out
assert out["slicer_receipt_authorized"] is False,out
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0,out

# Removing a closure must remove its derived binding, so frozen candidate no longer verifies.
mut=copy.deepcopy(trans)
mut["evidence"]=[x for x in mut["evidence"] if x.get("family")!="SUBAGENT_DELEGATION_AND_COORDINATION"]
bad=evaluate(reg,mut,man,bridge,shas)
assert bad["pass"] is False,bad
assert "BINDINGS_NOT_EXACT_RECOMPUTATION" in bad["errors"],bad

# Name-only invented mapping remains forbidden.
m=copy.deepcopy(bridge)
m["bindings"].append({
 "component_id":"memory",
 "interface_id":"browser/computer action+memory+recovery",
 "behavior_id":"INVENTED",
 "source_family":"LONG_HORIZON_MEMORY_AND_CONTINUITY",
 "closure_evidence_id":"INVENTED",
 "source_witness_path":"x",
 "independent_verification":"x",
 "proved_properties":["SCOPED_ACCEPTANCE_PROOF"]
})
bad=evaluate(reg,trans,man,m,shas)
assert bad["pass"] is False,bad

# Candidate must not self-authorize slicer receipts.
m=copy.deepcopy(bridge)
m["verification_state"]["slicer_receipt_authorized"]=True
bad=evaluate(reg,trans,man,m,shas)
assert bad["pass"] is False,bad

print("independent composition behavioral bridge verification: PASS")
