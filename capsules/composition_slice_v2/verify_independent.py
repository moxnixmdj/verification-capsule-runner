from __future__ import annotations
import hashlib,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXPECTED={
    "canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V1.json": "adc7db65b20361be54fa26935e36aa88babf373d",
    "canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_ACTIVATION_V1.json": "59504f4608f9490022c1aa58214e34191fb0b6e9",
    "canonical/verification/COMPOSITION_BEHAVIORAL_BRIDGE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "11784ce21ea55506559bc6fb8752b2b1b5585af5",
    "canonical/runtime/composition_component_proof_slicer_v1.py": "0e5028d8547bc3e17e7128b6311f734ac30a16d8",
    "canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V2.json": "f181afe329253176f2b86ce65c568dc3a133f6f2",
    "canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_20261002_V2.json": "714d1771ad2fa3ca240c0fb73609dc4873ea4390",
    "canonical/tests/test_composition_component_proof_slice_v2.py": "3482d3d5aa5978c15770e6a8616913e70814914f"
}
def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for rel,sha in EXPECTED.items():
    got=blob(ROOT/rel)
    assert got==sha,(rel,got,sha)
subprocess.run([sys.executable,"canonical/tests/test_composition_component_proof_slice_v2.py"],cwd=ROOT,check=True)
print("independent composition slice v2 verification: PASS")
