from __future__ import annotations
import hashlib, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXPECTED={
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json": "ee187f611a0e82b2de495ee377682f39bc31dd31",
    "canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json": "96052a6b5178305b37a2526fb25c3f53fa33b9b5",
    "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json": "9efbf3e81e67fbd15e34be2fcd86fbfc626b246d",
    "canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json": "d6cb17f548493e64ca3d200d51b049412a939ef7",
    "canonical/verification/COMPOSITION_BEHAVIORAL_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "bb9ecf9b34e3a41d8cd9a387fe70d9376accbccc",
    "canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V1.json": "adc7db65b20361be54fa26935e36aa88babf373d",
    "canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_ACTIVATION_V1.json": "59504f4608f9490022c1aa58214e34191fb0b6e9",
    "canonical/runtime/composition_behavioral_bridge_verifier_v1.py": "d6bfd80bab2742332ceb3c4105e535202ae00b20",
    "canonical/runtime/composition_component_proof_slicer_v1.py": "0e5028d8547bc3e17e7128b6311f734ac30a16d8",
    "canonical/runtime/composition_behavioral_bridge_activation_verifier_v1.py": "55278d01e3815b308b3007885971a4e129d42ed2",
    "canonical/tests/test_composition_behavioral_bridge_activation_v1.py": "7003a2e8c53129af39937f517a4d0c8c14d4e7d1"
}
def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for rel,sha in EXPECTED.items():
    got=blob(ROOT/rel)
    assert got==sha,(rel,got,sha)
subprocess.run([sys.executable,"canonical/tests/test_composition_behavioral_bridge_activation_v1.py"],cwd=ROOT,check=True)
subprocess.run([sys.executable,"canonical/runtime/composition_behavioral_bridge_activation_verifier_v1.py"],cwd=ROOT,check=True)
print("independent composition bridge activation verification: PASS")
