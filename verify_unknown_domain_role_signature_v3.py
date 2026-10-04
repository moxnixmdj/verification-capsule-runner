#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from canonical.runtime import unknown_domain_direct_candidate_v2 as v2
from canonical.runtime import unknown_domain_direct_candidate_v3 as v3
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as gen
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py": "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py": "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_candidate_v3.py": "6a56cbd8e9aac8730fb87e5e64d1ca031ce77395",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py": "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py": "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py": "e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py": "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
}


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


for rel, expected in EXPECTED.items():
    got = git_blob(ROOT / rel)
    assert got == expected, (rel, got, expected)

# This part is universal over the frozen generator's secret/beacon input:
# ADD2 exists only at transfer indices 4 and 10. Magnitudes are strictly
# positive. The sign formulas are independent of secret, beacon and domain.
for index in (4, 10):
    r0 = tuple(-1 if (j + index) % 2 == 0 else 1 for j in range(3))
    r1 = tuple(-1 if (j + index + 1) % 3 == 0 else 1 for j in range(3))
    assert r0 == (-1, 1, -1), (index, r0)
    assert r1 == (1, -1, 1), (index, r1)
    assert r0 != r1

# Deterministic zero-production witness for the exact binary64 defect in V2,
# then proof-by-execution that V3 repairs that same frozen case.
beacon = "FLOAT-ROLE-SWAP-000000000004"
packet = gen.generate_qualification_fixture_population(beacon=beacon)
visible = packet["visible_cases"][4]
hidden = packet["hidden_records"][4]

old = harness.execute_case(
    candidate_step=v2.step,
    case_visible=visible,
    hidden_record=hidden,
)
assert old["scorer_result"]["pass"] is False, old
assert "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in old["scorer_result"]["errors"], old

fixed = harness.execute_case(
    candidate_step=v3.step,
    case_visible=visible,
    hidden_record=hidden,
)
assert fixed["scorer_result"]["pass"] is True, fixed
assert fixed["probe_count"] < 3, fixed

# Broad independent qualification-only search. This is not the universal proof;
# it is regression pressure around the analytical invariant above.
checked = 0
for n in range(64):
    packet = gen.generate_qualification_fixture_population(
        beacon=f"V3-INDEPENDENT-QUAL-{n:012d}"
    )
    assert packet["production"] is False
    for case, hidden in zip(packet["visible_cases"], packet["hidden_records"]):
        out = harness.execute_case(
            candidate_step=v3.step,
            case_visible=case,
            hidden_record=hidden,
        )
        assert out["scorer_result"]["pass"] is True, (
            n, case["case_id"], out
        )
        assert out["probe_count"] < 3, out
        checked += 1

print(json.dumps({
    "schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_ROLE_SIGNATURE_V3_VERIFICATION_V1",
    "status": "PASS",
    "target_predicate": "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
    "v2_one_ulp_counterexample_reproduced": True,
    "v3_same_case_pass": True,
    "universal_add2_source_role_signatures": {
        "r0": [-1, 1, -1],
        "r1": [1, -1, 1],
        "indices": [4, 10],
    },
    "qualification_only_cases_checked": checked,
    "production_cases_consumed": 0,
    "new_reality_units_consumed": 0,
    "incremental_spend_usd": 0,
    "acceptance_credit_delta": 0,
    "promotion_authority": False,
}, sort_keys=True))
