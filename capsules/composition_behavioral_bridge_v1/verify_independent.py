from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXPECTED={
    "canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json": "d6cb17f548493e64ca3d200d51b049412a939ef7",
    "canonical/runtime/composition_behavioral_bridge_verifier_v1.py": "d6bfd80bab2742332ceb3c4105e535202ae00b20",
    "canonical/tests/test_composition_behavioral_bridge_v1.py": "1b768b99f1db6664ed078e6ffa2e1d522ffb59b1",
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json": "ee187f611a0e82b2de495ee377682f39bc31dd31",
    "canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json": "96052a6b5178305b37a2526fb25c3f53fa33b9b5",
    "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json": "9efbf3e81e67fbd15e34be2fcd86fbfc626b246d"
}
def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for rel,sha in EXPECTED.items():
    got=blob(ROOT/rel)
    assert got==sha,(rel,got,sha)
subprocess.run([sys.executable,"canonical/tests/test_composition_behavioral_bridge_v1.py"],cwd=ROOT,check=True)
sys.path.insert(0,str(ROOT))
from canonical.runtime.composition_behavioral_bridge_verifier_v1 import evaluate,git_blob_sha
def load(rel): return json.loads((ROOT/rel).read_text())
reg=load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")
trans=load("canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json")
man=load("canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json")
bridge=load("canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json")
out=evaluate(reg,trans,man,bridge,{"registry":git_blob_sha(ROOT/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),"transmutation":git_blob_sha(ROOT/"canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json"),"manifest":git_blob_sha(ROOT/"canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json")})
assert out["pass"] is True,out
assert out["derived_binding_count"]==2,out
assert {x["component_id"] for x in out["derived_bindings"]}=={"delegation","tool discovery"},out
assert out["slicer_receipt_authorized"] is False,out
print("independent composition behavioral bridge verification: PASS")
