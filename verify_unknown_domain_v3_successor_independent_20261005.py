#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/unknown_domain_v3_successor_20261005"
sys.path.insert(0, str(SUBJECT))

EXPECTED = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py": "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py": "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_candidate_v3.py": "cb030de5a7f96bac7667b7fbb3be38a1cc55e3ea",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py": "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py": "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v3.py": "3c8b75db986739004bee5b206be5033989d25e9a",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py": "e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py": "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
}

def blob(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

for rel, expected in EXPECTED.items():
    got = blob(SUBJECT / rel)
    assert got == expected, (rel, got, expected)

from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer

# 1) Exact reachable V2 falsifier must be repaired without relaxing scorer semantics.
secret = hashlib.sha256(b"secret0").digest()
beacon = "beacon-qualification-0000000000000000"
visible, hidden = g2._transfer_case(secret, beacon, 4, namespace="REVOCATION")
old_gold = hidden["gold_terminal_consequence"]
out = harness.execute_case(candidate_step=c3.step, case_visible=visible, hidden_record=hidden)
assert out["scorer_result"]["pass"] is True, out
assert out["candidate_terminal_action"]["terminal_consequence"] == old_gold
assert out["probe_count"] == 1

# 2) Prove identifier uniqueness does not depend on HMAC suffix collision resistance.
# Force every token used *inside the ID constructor* to collide. Slot ordinals must
# still make all labels unique, while the HMAC-ranked semantic assignment remains
# opaque in the real implementation.
orig_token = g1._token
try:
    g1._token = lambda *args, **kwargs: "COLLISION"
    m, d = g3._surface_ids_total(b"x"*32, "B"*20, 4, "TEST_A", ["r0", "r1"])
    vals = list(m.values()) + list(d)
    assert len(vals) == len(set(vals)) == 4
finally:
    g1._token = orig_token

# 3) Source and target ADD2 role signatures must be identifying for both ADD2 indices.
for idx in (4, 10):
    for k in range(128):
        secret = hashlib.sha256(f"sig-{idx}-{k}".encode()).digest()
        beacon = "SIG-" + hashlib.sha256(f"{idx}:{k}".encode()).hexdigest()[:24]
        visible, hidden = g3._transfer_case(secret, beacon, idx, namespace=f"S{k}")
        rec = visible["domain_a"]["earned_receipts"][0]
        oriented = c3._orient_add2(
            visible, rec, hidden["transfer_relevant_feature_ids"]
        )
        assert oriented == hidden["domain_mapping"], (idx, k, oriented, hidden["domain_mapping"])

# 4) Deterministic end-to-end falsification sweep over exact V3 generator/candidate.
POPULATIONS = 1024
cases = 0
probe_hist = {}
family_hist = {}
for k in range(POPULATIONS):
    secret = hashlib.sha256(f"v3-independent-secret-{k}".encode()).digest()
    beacon = "V3-INDEPENDENT-" + hashlib.sha256(f"beacon-{k}".encode()).hexdigest()[:24]
    packet = g3._generate(beacon=beacon, evaluator_secret=secret, namespace=f"IV3{k}")
    assert packet["case_count"] == 27
    results = []
    for visible, hidden in zip(packet["visible_cases"], packet["hidden_records"], strict=True):
        ex = harness.execute_case(candidate_step=c3.step, case_visible=visible, hidden_record=hidden)
        r = ex["scorer_result"]
        if r["pass"] is not True:
            raise AssertionError(json.dumps({
                "population": k,
                "case_id": visible["case_id"],
                "hidden": hidden,
                "execution": ex,
            }, sort_keys=True))
        results.append(r)
        cases += 1
        probe_hist[str(ex["probe_count"])] = probe_hist.get(str(ex["probe_count"]), 0) + 1
        if hidden["leaf_id"] == g1.TRANSFER:
            fam = str(hidden["primitive_family"])
            family_hist[fam] = family_hist.get(fam, 0) + 1
    assert scorer.aggregate(results)["all_27_cases_pass"] is True

receipt = {
    "schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_V3_INDEPENDENT_SUCCESSOR_VERIFICATION_V1",
    "status": "PASS__EXACT_FLOAT_COUNTEREXAMPLE_REPAIRED__STRUCTURAL_ID_TOTALITY_TESTED__END_TO_END_FALSIFICATION_PASS",
    "exact_subject_blobs": EXPECTED,
    "v2_counterexample_repaired": True,
    "forced_identifier_suffix_collision_still_unique": True,
    "add2_role_signature_indices_verified": [4, 10],
    "add2_role_signature_trials": 256,
    "synthetic_falsification": {
        "populations": POPULATIONS,
        "cases": cases,
        "probe_histogram": probe_hist,
        "transfer_family_histogram": family_hist,
        "all_exact_hidden_scorer_pass": True,
    },
    "hard_nonclaims": [
        "FINITE_FALSIFICATION_IS_NOT_BY_ITSELF_A_UNIVERSAL_PROOF",
        "NO_OPEN_WORLD_GENERALIZATION_BEYOND_THE_BOUND_GENERATOR_FAMILY",
        "NO_PRODUCTION_OR_TERMINAL_CASES_CONSUMED",
        "NO_ACCEPTANCE_OR_OWNERSHIP_CREDIT_GRANTED_BY_THIS VERIFIER",
    ],
    "accounting": {
        "incremental_spend_usd": 0,
        "production_cases_consumed": 0,
        "terminal_cases_consumed": 0,
        "acceptance_credit_delta": 0,
    },
}
Path("unknown_domain_v3_independent_successor_verification_v1.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
print(json.dumps(receipt, sort_keys=True))
