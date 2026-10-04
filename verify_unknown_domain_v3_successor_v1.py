#!/usr/bin/env python3
from __future__ import annotations
import hashlib
from pathlib import Path

ROOT=Path("capsules/unknown-domain-v3")
EXPECTED={
"canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
"canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
"canonical/runtime/unknown_domain_direct_candidate_v3.py":"afafbf729940d6b77b65a76f78e5b241d30a9ed9",
"canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
"canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
"canonical/runtime/unknown_domain_direct_hidden_generator_v3.py":"7e2b4627812e1b1d2c3923ad6c1138a5d90ef923",
"canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
"canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
"canonical/tests/test_unknown_domain_direct_v3_successor.py":"3226e7bb9978a0d57140d6795c9b62e82acf00ce",
}
def blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
for rel,exp in EXPECTED.items():
    got=blob((ROOT/rel).read_bytes())
    assert got==exp,(rel,got,exp)
candidate=(ROOT/"canonical/runtime/unknown_domain_direct_candidate_v3.py").read_text()
generator=(ROOT/"canonical/runtime/unknown_domain_direct_hidden_generator_v3.py").read_text()
tests=(ROOT/"canonical/tests/test_unknown_domain_direct_v3_successor.py").read_text()
assert "hidden_record" not in candidate
assert "evaluator_secret" not in candidate
assert "hidden_generator" not in candidate
up=generator.index("def _upgrade")
segment=generator[up:]
assert segment.index("_assert_identifier_totality(packet)") < segment.index("return out")
assert "generate_production_population" not in tests
assert "test_v3_closes_exact_v2_add2_counterexample" in tests
assert "32" in tests and "27" in tests
print("UNKNOWN_DOMAIN_V3_EXACT_BYTES_AND_STATIC_GATES_PASS")
