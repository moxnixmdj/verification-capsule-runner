from __future__ import annotations
import hashlib
import json
from pathlib import Path

from canonical.runtime.p1_composite_proof_counterexample_audit_v1 import evaluate

ROOT=Path(__file__).resolve().parent
EXPECTED={
"canonical/runtime/p1_composite_proof_counterexample_audit_v1.py":"1ad4505335bfc45e6fecb08c606604651d7779bd",
"canonical/tests/test_p1_composite_proof_counterexample_audit_v1.py":"e6e399cbeaaf2aa17031fdcd54b46fc4a66d504a",
"canonical/governance/P1_COMPOSITE_PROOF_COUNTEREXAMPLE_QUARANTINE_V1.json":"128f259714617da2127e38dfd53682040d5a7126",
"canonical/governance/P1_COMPOSITE_PROOF_ROLE_RECONCILIATION_V1.json":"700381c22715dbd058370bddc07f99888a9bc97a",
"canonical/runtime/trajectory_failure_typed_ir_candidate_v4.py":"0c386e6b78a8e97e9c1944e63600047bc4e2849b",
"canonical/runtime/trajectory_failure_typed_ir_proof_v4.py":"6e1dfaa6b63fc629d55d07b2361bf625f11a5ce3",
"canonical/runtime/contract_native_brain_candidate.py":"afc18af1d1da6f25166c6cc57dcbc0cd3070bb85",
"canonical/runtime/contract_native_proof_suites.py":"0210790c7dd705ef328e1b55d529a30c5c6c3337",
}
def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for rel,expected in EXPECTED.items():
    got=blob(ROOT/rel)
    assert got==expected,(rel,got,expected)
out=evaluate()
assert out["audit_valid"] is True,out
assert out["candidate_composite_restoration_admissible"] is False,out
assert out["whole_p1_contract_restored"] is False,out
assert out["counterexamples"]["v4_dropped_provenance"]["counterexample_holds"] is True,out
assert out["counterexamples"]["terminal_unfalsifiable_diagnosis"]["counterexample_holds"] is True,out
assert out["terminal_results_replayed"]==0,out
assert out["new_reality_units_consumed"]==0,out
assert out["promotion_authority"] is False,out
print(json.dumps({
 "status":"INDEPENDENT_P1_COMPOSITE_COUNTEREXAMPLES_PASS",
 "exact_blob_count":len(EXPECTED),
 "counterexample_count":2,
 "composite_restoration_admissible":False,
 "terminal_results_replayed":0,
 "new_reality_units_consumed":0
},indent=2,sort_keys=True))
