from __future__ import annotations
import hashlib
import json
from pathlib import Path

from canonical.runtime.recovery_t0_t2_acceptance_ceiling_lifter_v1 import (
    _semantic_relation_errors,
)

ROOT=Path(__file__).resolve().parent
EXPECTED={
"canonical/runtime/recovery_t0_t2_acceptance_ceiling_lifter_v1.py":"d61a826b9da0a287015298612de619fb97f3082b",
"canonical/tests/test_recovery_t0_t2_acceptance_ceiling_lifter_v1.py":"9dd96f77169e188d5ff4ac8372b6554c7d140b35",
"canonical/governance/RECOVERY_EARLIEST_NONIMPLICATION_CERTIFICATE_V1.json":"ce4c05b1baa9fcf8111b12788ed6cf1cc96b034d",
"canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":"eb4bca0fe6a015d49d2854998fbe046c979c7ea9",
"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json":"ee187f611a0e82b2de495ee377682f39bc31dd31",
"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
"canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json":"8703c6aa08227467a619a7ae90d0d61f8e54da39",
"canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json":"bd86b4c53992b47a4a60b64a60ba03db9a442cfc",
"canonical/governance/RECOVERY_T0_T2_ACCEPTANCE_SCOPE_RELATION_V1.json":"5159f145fad8b07fe2164716aedf653a0b34a6e0",
"canonical/governance/P1_TERMINAL_EXECUTION_SCOPE_MISMATCH_QUARANTINE_V1.json":"fb939e0e3ff1fe2476de79596a71110510eed0d8",
}

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel,expected in EXPECTED.items():
    got=blob(ROOT/rel)
    assert got==expected,(rel,got,expected)

relation=json.loads((ROOT/"canonical/governance/RECOVERY_T0_T2_ACCEPTANCE_SCOPE_RELATION_V1.json").read_text())
errors=_semantic_relation_errors(relation)
assert "RELATION_STRICT_EARLIEST_TARGET_HAS_NO_STRICT_SOURCE_PROOF" in errors,errors
assert "RELATION_EARLIEST_TARGET_WEAKENED_TO_EARLIEST_OR_CRITICAL" in errors,errors
assert "CAUSAL_LOCALIZATION_CEILING_DERIVED_FROM_WEAKER_DISJUNCTION" in errors,errors

critical=True
earliest=False
assert (critical or earliest) is True
assert earliest is False

print(json.dumps({
 "status":"INDEPENDENT_RECOVERY_EARLIEST_NONIMPLICATION_GUARD_PASS",
 "exact_blob_count":len(EXPECTED),
 "semantic_guard_errors":errors,
 "countermodel":{"critical":True,"earliest":False,"source_or":True,"strict_target":False}
},indent=2,sort_keys=True))
