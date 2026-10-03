from __future__ import annotations
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
"canonical/runtime/branchless_proof_promotion_gate_v1.py":"7717e92ba31579ff475e6f85fb0e1c2432362430",
"canonical/tests/test_branchless_proof_reuse_v1.py":"bdfa1862080bdd2b28760dad60dd3bc2d2da029a",
"canonical/runtime/terminal_information_cut_compiler_v1.py":"d6515b3dad63a74cf1b1eaff6438a4964f7b1d84",
"canonical/tests/test_information_cut_v1.py":"1c91f9caec02162f3876022f50fdaf416c3a678c",
"canonical/runtime/terminal_closure_supertransaction_guard_v1.py":"c8784599fddce5b861839975561ccbba1edf58ed",
"canonical/tests/test_terminal_closure_transaction_v1.py":"1ca328578431477821328d92042b36bcda0b0479",
"canonical/governance/TERMINAL_LATENCY_COLLAPSE_STACK_V1.json":"a4daf20ef21b52bfa1664115263495bc5ad8dd7c",
"canonical/action_intents/2026-10-03_TERMINAL_LATENCY_COLLAPSE_STACK_V1.json":"1aafd88807bea2ce222a9de772341f89b10221d2",
}
def blob_sha(path:Path)->str:
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode())
    h.update(data)
    return h.hexdigest()
for rel,expected in EXPECTED.items():
    actual=blob_sha(ROOT/rel)
    assert actual==expected,(rel,expected,actual)
sys.path.insert(0,str(ROOT))
names=[
"canonical.tests.test_branchless_proof_reuse_v1",
"canonical.tests.test_information_cut_v1",
"canonical.tests.test_terminal_closure_transaction_v1",
]
suite=unittest.defaultTestLoader.loadTestsFromNames(names)
result=unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful()
g=json.loads((ROOT/"canonical/governance/TERMINAL_LATENCY_COLLAPSE_STACK_V1.json").read_text())
assert g["protected_truth"]["accepted_families"]=="3_OF_19"
assert g["protected_truth"]["atomic_acceptance"]=="8_OF_38_PROVED__30_UNRESOLVED"
assert g["protected_truth"]["terminal_goal_achieved"] is False
assert g["new_reality_units_consumed"]==0
assert g["capability_credit_delta"]==0
assert g["family_credit_delta"]==0
assert g["execution_authority"] is False
assert g["promotion_authority"] is False
print("TERMINAL_LATENCY_COLLAPSE_STACK_EXACT_BYTES_AND_TESTS_PASS")
