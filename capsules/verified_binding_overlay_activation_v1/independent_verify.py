import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
"canonical/governance/VERIFIED_WITNESS_TARGET_OVERLAY_MANIFEST_V1.json":"e627c2c1d9aa70cf6be42b40e249f4a5bfb9e64d",
"canonical/runtime/protocol_implication_overlay_batch_reducer_v1.py":"a3d3cd421f5e9439283b0e127bda0876d17c3561",
"canonical/verification/VERIFIED_WITNESS_TARGET_OVERLAYS_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"bb1f1608817be3b1b18f838f9ffd5418437dacd8",
"canonical/governance/VERIFIED_WITNESS_TARGET_OVERLAY_ACTIVATION_V1.json":"e777937ca1774d7b20f3826bf7f51809c5c8d5c8",
"canonical/governance/EXECUTION_FIRST_SELF_PROVING_OPTIMIZER_V1.json":"c1a4a29d27b60aa367e491d7d1d1a2d449331497",
"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":"7d0875c45374922b9c2b6f3a519977a209da6cee",
"canonical/tests/test_verified_witness_target_overlay_activation_v1.py":"583794536df17bba9618f186ce1a9c48554f6950"
}
def blob(rel):
    data=(ROOT/rel).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()
for rel,exp in EXPECTED.items():
    actual=blob(rel)
    assert actual==exp,(rel,actual,exp)
def load(rel): return json.loads((ROOT/rel).read_text())
activation=load("canonical/governance/VERIFIED_WITNESS_TARGET_OVERLAY_ACTIVATION_V1.json")
receipt=load("canonical/verification/VERIFIED_WITNESS_TARGET_OVERLAYS_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
optimizer=load("canonical/governance/EXECUTION_FIRST_SELF_PROVING_OPTIMIZER_V1.json")
authority=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
assert activation["status"].startswith("ACTIVE_INDEPENDENT_PASS")
assert receipt["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert optimizer["proof_compression_kernels"]["protocol_implication_scope_algebra"]=="canonical/runtime/protocol_implication_scope_algebra_v2.py"
assert optimizer["proof_compression_kernels"]["verified_witness_target_overlay_activation"]=="canonical/governance/VERIFIED_WITNESS_TARGET_OVERLAY_ACTIVATION_V1.json"
assert optimizer["verified_semantic_overlay_compilation"]["runtime"]=="canonical/runtime/protocol_implication_overlay_batch_reducer_v1.py"
assert authority["truth"]["opus55_acceptance"]=="2/19_PASS__17/19_OPEN"
assert authority["truth"]["achieved"] is False
assert activation["current_projection"]["improved_target_count"]==1
assert activation["current_projection"]["closed_target_count"]==0
assert activation["capability_credit_delta"]==0 and activation["family_credit_delta"]==0
assert activation["execution_authority"] is False and activation["promotion_authority"] is False
print("independent verified binding overlay activation check: PASS")
